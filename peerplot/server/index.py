#!/usr/bin/env python
"""
PeerPlot - matplotlib on the cloud

Copyright (c) 2012, Brian Refsdal (brian.refsdal@gmail.com)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

# Inspiration for this server came from the Tornado websocket
# and Eventlet websocket demos



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

TOKEN_SIZE = 6
HOST='localhost'
PORT=80
SECRET=str(base64.b64encode(hashlib.sha256(str(random.random())).digest()))

define("port", default=PORT, help="run on the given port", type=int)
define("host", default=HOST, help="run on the given address", type=str)

_tokens = string.ascii_letters + string.digits

def generate_token():
    return ''.join(random.sample(_tokens, TOKEN_SIZE))

def parse_token(resource, path_info):
    path = str(path_info).strip().strip('/')
    return path.replace(resource, '').strip('/')

def write_message(sock, message):
    try:
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


class Session(object):
    """
    Session object encapsulates a generated PeerPlot meeting as a collection
    of WebSocket connections.  One connection is considered the administrator.
    This privilege can be passed from connection to connection.
    """
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


class Application(tornado.web.Application):
    """
    Main Tornado web framework object.  Associates URLs to handlers.
    """
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/downloads/(.*)", StaticFileHandler,
             {"path" : os.path.join(os.path.dirname(__file__), "downloads") }),
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


class ManagerSocketHandler(WebSocketHandler):
    """
    A WebSocket handler to manage user list and administrator updates per session

    Browser --> web server --> Browser
    """

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

        # If a user (an admin by rule) is the last to leave, discard the session after he disconnects
        if not managers:
            logging.info("[%s] last user '%s' has left the session, cleaning up..."  % (session.hashid, str(self.connection.name)))
            _sessions.pop(session)


    def on_message(self, message):
        session = self.get_session()
        if session is None:
            return
        if message.strip() == '':
            return
        managers = session.managers
        admin = session.admin
        msg = json.loads(message)

        if msg.has_key("admin"):
            for master in admin:
                write_message(master, json.dumps({"enabled": False}))
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
            logging.info("[%s] user '%s' is now the admin" % (session.hashid, str(connection.name)))

        elif msg.has_key("name"):
            logging.info("[%s] new user '%s' has joined" % (session.hashid, msg["name"]))
            self.connection.name = msg["name"]

        update_user_list(session)


class APISocketHandler(WebSocketHandler):
    """
    A WebSocket handler to manage the plotting API functions between
    the browser and the web server.

    Browser --> web server --> Matplotlib
    """


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
    """
    A WebSocket handler to connect the web server to the Matplotlib
    client.  Implements the broadcast to all connected browser clients
    per session.

                              --> browser 1
                              |
    Matplotlib --> web server --> browser 2
                              |
                              --> browser i
    """

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
    """
    Main HTTP handler for the PeerPlot session pages
    """

    def get(self):
        script = str(self.request.uri).strip()
        token = script.strip('/')
        if _sessions.has_key(token):
            self.render("plot.html", session=token, server_ip=options.host, server_port=options.port)
        else:
            self.send_error(404, token=token)

    def write_error(self, status_code, **kwargs):
        token = kwargs.pop('token', '')
        if status_code == 404:
            message = "The session '%(token)s' is not found, try generating a new session" % {
                "token": token
                }
            self.finish("<html><title>%(code)d: %(message)s</title>"
                        "<body>%(code)d: %(message)s</body></html>" % {
                    "code": status_code,
                    "message": message
                    })
            return
        RequestHandler.write_error(self, status_code, **kwargs)


class MainHandler(RequestHandler):
    """
    Main HTTP handler for the PeerPlot home page
    """

    def get(self):
        self.render("index.html")


class GenerateHandler(RequestHandler):
    """
    HTTP handler to generate a new PeerPlot session as a 6 character hash
    redirects the user to the new URL.
    """

    def post(self):
        hashid = generate_token()  # generate string tokens

        # What if hashid already exists in _sessions?
        # Presence of a hashing collision
        count = 0
        while hashid in _sessions:
            hashid = generate_token()
            count += 1
            if count > 5:
                self.send_error(403)
                return

        _sessions[hashid] = Session(hashid)

        url = 'http://' + options.host + ':' + str(options.port) + '/' + hashid
        self.redirect(url)

    def write_error(self, status_code, **kwargs):
        if status_code == 403:
            script = str(self.request.uri).strip()
            token = script.strip('/')
            self.finish("<html><title>%(code)d: %(message)s</title>"
                        "<body>%(code)d: %(message)s</body></html>" % {
                    "code": status_code,
                    "message": "PeerPlot failed to create a session, please try again later"
                    })
            return
        RequestHandler.write_error(self, status_code, **kwargs)


class Connection(object):
    """
    A class to encapsulate a WebSocket connection with an associated ID and username
    """
    def __init__(self, address):
        self.name = None
        self.id = str(uuid.uuid4())
        self.handler = None
        self.address = address
        self.isadmin = False


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port, options.host)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
