#!/usr/bin/env python

import sys
import time
import logging
import thread
import string
import random
import urllib
import urllib2
import cookielib
import eventlet
import multiprocessing
from peerplot.websocket import WebSocketApp

_ncpus = multiprocessing.cpu_count()
#pool = multiprocessing.Pool(_ncpus)
#pmap = pool.map_async
pool = eventlet.GreenPool()
pmap = pool.imap

_tokens = string.ascii_letters + string.digits

HOME = "http://www.peerplot.com"
GENERATE = "http://www.peerplot.com/generate"
TOKEN_SIZE = 6
NUM_SESSIONS = 100

def generate_token():
    return ''.join(random.sample(_tokens, TOKEN_SIZE))

def generate_tokens(num):
    return map(lambda ii: generate_token(), range(num))

class CookieFactory(object):
    def __call__(self, home, generate):

        #def worker(*args):
        #    return CookieMiner(home, generate).sessionid

        def worker(*args):
            cj = cookielib.CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
            url = opener.open(home)
            cookie = url.headers.values()[0].split(";")[0].split("=")[1]
            s = opener.open(generate, urllib.urlencode(dict(_xsrf=cookie)))
            sessionid = s.url[-6:]
            return sessionid

        return map(worker, range(NUM_SESSIONS))

class CookieMiner(object):

    def __init__(self, home, generate):

        cj = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        url = opener.open(home)
        self.cookie = url.headers.values()[0].split(";")[0].split("=")[1]
        print 'cookie', self.cookie
        s = opener.open(generate, urllib.urlencode(dict(_xsrf=self.cookie)))
        self.sessionid = s.url[-6:]


class SessionFactory(object):

    stream = sys.stdout

    mgmt_url = 'ws://peerplot.dce.harvard.edu:80/browser/%s'
    api_url = 'ws://peerplot.dce.harvard.edu:80/api/%s'

    #sessions = [ 'brian', 'chris', 'linds' ]
    #sessions = generate_tokens(NUM_SESSIONS)
    sessions = None

    def __call__(self):
        return [Session(self.stream, self.mgmt_url, self.api_url, sessionid)
                for sessionid in self.sessions]

class Session(object):

    def __init__(self, stream, mgmt_url, api_url, sessionid):

        formatter = logging.Formatter(fmt='%(asctime)s %(name)s: %(message)s')
        handler = logging.StreamHandler(stream)
        handler.setFormatter(formatter)

        blogger = logging.getLogger("("+sessionid+")"+"browser")
        blogger.level = logging.INFO
        blogger.addHandler(handler)
        browser_info = blogger.info

        alogger = logging.getLogger("("+sessionid+")"+"api")
        alogger.level = logging.INFO
        alogger.addHandler(handler)
        api_info = alogger.info

        def browser_onopen(sock):
            try:
                time.sleep(1)
                message = '{ "name" : "' + sessionid + '"}'
                sock.send(message)
                browser_info("[onopen] " + str(message))
            except Exception, e:
                browser_info(str(e))

        def browser_onmessage(sock, msg):
            browser_info("[onmessage] " + str(msg))

        def browser_onerror(sock, error):
            browser_info("[onerror] " + str(error))

        def browser_onclose(sock):
            browser_info("[onclose] socket closed")

        browser_info("Connecting to %s..."%(mgmt_url%(sessionid)))
        self.management_socket = WebSocketApp(mgmt_url%(sessionid),
                                              on_open=browser_onopen,
                                              on_message=browser_onmessage,
                                              on_error=browser_onerror,
                                              on_close=browser_onclose)

        self.browser_thread = thread.start_new_thread(self.management_socket.run_forever, ())

        def api_onopen(sock):
            time.sleep(1)
            msg = "<hello args=''>"
            sock.send(msg)
            api_info("[onopen] " + str(msg))

        def api_onmessage(sock, msg):
            brief = str(msg)
            if len(brief) > 500:
                brief = brief[:500]

            api_info("[onmessage] " + brief)

        def api_onerror(sock, error):
            api_info("[onerror] " + str(error))

        def api_onclose(sock, msg):
            api_info("[onclose] socket closed")

        api_info("Connecting to %s..."%(api_url%(sessionid)))
        self.api_socket = WebSocketApp(api_url%(sessionid),
                                       on_open=api_onopen,
                                       on_message=api_onmessage,
                                       on_error=api_onerror,
                                       on_close=api_onclose)
        self.api_thread = thread.start_new_thread(self.api_socket.run_forever, ())


if __name__ == '__main__':

    factory = CookieFactory()
    tt = time.time()
    SessionFactory.sessions = factory(HOME, GENERATE)
    print 'Created ', NUM_SESSIONS, ' sessions in %g secs'%(time.time()-tt)

    factory = SessionFactory()
    clients = factory()
