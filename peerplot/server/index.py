#!/usr/bin/env python
"""
PeerPlot - matplotlib on the cloud

Copyright (c) 2011, Brian Refsdal (brian.refsdal@gmail.com)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

# Inspiration for this server came from the Tornado websocket demo



import os
import os.path
import sys
import time
import base64
import hashlib
import random
import string
import uuid
import logging
import socket
import json

import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
from tornado.websocket import WebSocketHandler
from tornado.web import RequestHandler, StaticFileHandler
from tornado.options import define, options

HOST='peerplot.dce.harvard.edu'
PORT=80
SECRET=str(base64.b64encode(hashlib.sha256(str(random.random())).digest()))

define("port", default=PORT, help="run on the given port", type=int)
define("host", default=HOST, help="run on the given address", type=str)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/downloads/(.*)", StaticFileHandler, {"path" : os.path.join(os.path.dirname(__file__), "downloads") }),
            (r"/generate", GenerateHandler),
            (r"/manager/.*", ManagerSocketHandler),
            (r"/api/.*", APISocketHandler),
            (r"/client/.*", ClientSocketHandler),
            (r"/.*", SessionHandler),
        ]
        settings = dict(
            cookie_secret=SECRET,
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
            autoescape=None,
        )
        tornado.web.Application.__init__(self, handlers, **settings)



def write_message(sock, message):
    try:
        # if type(message) not in (str,):
        #     #print 'message...', str(message)
        #     #message = "'%s'" % json.dumps(message, ensure_ascii=True)
        #     message = json.dumps(message, ensure_ascii=True)

        #     #print 'converting message...', message
        #     #message = tornado.escape.utf8(message)
        #     #print 'converted message', message, type(message), list(message)
        #     #message = "clients=[];enabled=true;"

        sock.write_message(message)
    except IOError:
        logging.error("request '%s' closed" % str(sock.request.connection.address))
    except socket.error, e:
        logging.error("socket: " + str(e))
    except Exception, e:
        logging.error(str(type(e)) + str(e))
        raise


def update_user_list(session):
    names = session.names
    # msg_temp = str('clients=' + json.dumps(names) + ';')
    # admin_msg = msg_temp + 'admin=true;'
    # non_admin_msg = msg_temp + 'admin=false;'

    msg_temp = { 'clients': list(names) }
    admin_msg = dict([('admin',True)])
    admin_msg.update(msg_temp)
    non_admin_msg = dict([('admin',False)])
    non_admin_msg.update(msg_temp)

    for manager in session.managers:
        msg = non_admin_msg
        if manager in session.admin:
            msg = admin_msg
        write_message(manager, json.dumps(msg))


class ManagerSocketHandler(WebSocketHandler):

    def allow_draft76(self):
        return True

    def get_session(self):
        token = parse_token('manager', self.request.uri)
        session = _sessions.get(token, None)
        return session

    def open(self):
        session = self.get_session()
        if session is None:
            return
        managers = session.managers
        managers.append(self)

        address = self.request.connection.address
        logging.info("new connection " + str(address))
        connection = Connection(address)
        connection.handler = self
        self.connection = connection
        session.connections.append(connection)

        # If current request is the only element in manager, assume admin
        if len(managers) == 1:
            session.admin.add(self)
            connection.isadmin = True
            write_message(self, json.dumps({"enabled": True}))
            #write_message(self, "enabled=true;")
            logging.info("[%s] user '%s' is now the admin" % (session.hashid, str(connection.name)))

        update_user_list(session)

    def on_close(self):
        session = self.get_session()
        if session is None:
            return
        managers = session.managers
        admin = session.admin
        managers.remove(self)
        session.connections.remove(self.connection)
        logging.info("[%s] user '%s' is no longer the admin" % (session.hashid, str(self.connection.name)))

        if self in admin and managers:
            admin.add(managers[0])
            admin.remove(self)
            write_message(managers[0], json.dumps({"enabled": True}))
            #write_message(managers[0], "enabled=true;")
            managers[0].connection.isadmin = True
            logging.info("[%s] user '%s' is now the admin" % (session.hashid, str(managers[0].connection.name)))

        update_user_list(session)


    def on_message(self, message):
        session = self.get_session()
        if session is None:
            return
        if message.strip() == '':
            return
        managers = session.managers
        admin = session.admin
        #logging.info("loading JSON message: " + str(message))
        msg = json.loads(message)

        if msg.has_key("admin"):
            for master in admin:
                write_message(master, json.dumps({"enabled": False}))
                #write_message(master, "enabled=false;")
                master.connection.isadmin = False
            admin.clear()

            index = None
            try:
                index = int(msg["admin"])
            except:
                logging.error("Unable to parse admin index!")
                raise

            connection = session.connections[index]
            new_admin = connection.handler
            admin.add(new_admin)
            new_admin.connection.isadmin = True
            write_message(new_admin, json.dumps({"enabled": True}))
            #write_message(new_admin, "enabled=true;")
            logging.info("[%s] user '%s' is now the admin" % (session.hashid, str(connection.name)))

        elif msg.has_key("name"):
            logging.info("[%s] new user '%s' has joined" % (session.hashid, msg["name"]))
            self.connection.name = msg["name"]

        update_user_list(session)


class APISocketHandler(WebSocketHandler):

    def allow_draft76(self):
        return True

    def get_session(self):
        token = parse_token('api', self.request.uri)
        session = _sessions.get(token, None)
        return session


    def open(self):
        session = self.get_session()
        if session is None:
            return
        browsers = session.browsers
        browsers.add(self)
        #logging.info("API-open browsers: " + str(browsers))


    def on_close(self):
        session = self.get_session()
        if session is None:
            return
        browsers = session.browsers
        browsers.remove(self)


    def on_message(self, message):
        session = self.get_session()
        if session is None:
            return
        clients = session.clients
        for client in clients:
            write_message(client, message)


class ClientSocketHandler(WebSocketHandler):

    def get_session(self):
        token = parse_token('client', self.request.uri)
        session = _sessions.get(token, None)
        return session


    def open(self):
        session = self.get_session()
        if session is None:
            return
        clients = session.clients

        # Only allow one Python client per session
        if len(clients) > 0:
            return

        logging.info("[%s] new python client %s" %
                     (session.hashid, str(self.request.connection.address )))

        clients.add(self)
        browsers = session.browsers
        write_message(self, "<hello args=''")


    def on_close(self):
        session = self.get_session()
        if session is None:
            return
        clients = session.clients
        try:
            clients.remove(self)
        except:
            pass


    def on_message(self, message):
        session = self.get_session()
        if session is None:
            return
        session.cache = str(message)
        browsers = session.browsers
        for browser in browsers:
            write_message(browser, message)
            logging.info("[%s] client message to %s" %
                         (session.hashid, str(browser.request.connection.address)))

class SessionHandler(RequestHandler):

    def get(self):
        script = str(self.request.uri).strip()
        token = script.strip('/')
        if _sessions.has_key(token):
            self.render("plot.html", session=token, server_ip=options.host, server_port=options.port)
        else:
            self.send_error(404)


class MainHandler(RequestHandler):
    def get(self):
        self.render("index.html")


class GenerateHandler(RequestHandler):

    def post(self):
        # FIXME: What is the strategy for collisions?
        hashid = generate_token()  # generate string tokens
        _sessions[hashid] = Session(hashid)

        url = 'http://' + options.host + ':' + str(options.port) + '/' + hashid
        self.redirect(url)

_tokens = string.ascii_letters + string.digits
TOKEN_SIZE = 6

def generate_token():
    return ''.join(random.sample(_tokens, TOKEN_SIZE))

def parse_token(resource, path_info):
    path = str(path_info).strip().strip('/')
    return path.replace(resource, '').strip('/')



class Connection(object):

    def __init__(self, address):
        self.name = None
        self.id = str(uuid.uuid4())
        self.handler = None
        self.address = address
        self.isadmin = False


class Session(object):

    def _get_names(self):
        names = []
        for connection in self.connections:
            user = {}
            if connection.isadmin:
                user['admin'] = True
            name = user['name'] = "%s:%i"%connection.address
            if connection.name is not None:
                name = connection.name
            user['name'] = name
            names.append(user)
        return names

    def _set_names(self):
        raise NotImplementedError

    names = property(_get_names, _set_names)

    def __init__(self, hashid):
        self.hashid = hashid
        self.admin = set()
        self.managers = []
        self.browsers = set()
        self.clients = set()
        self.cache = ""

        self.connections = []

_sessions = { 'brian' : Session('brian'),
              'chris' : Session('chris') }



def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port, options.host)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
