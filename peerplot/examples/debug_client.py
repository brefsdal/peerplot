import thread
#from peerplot import client
from mymplh5canvas import client

HOST = 'localhost'
PORT = '80'
SESSION_ID = 'chris'

def web_socket_receive_data(client, request, message=None):
    while True:
        try:
            line = client._stream.receive_message().encode('utf-8')
            if not line:
                print 'connection closed...'
                return

            if len(line) > 100:
                print 'recieving message: ', line[:50]
            else:
                print 'recieving message: ', line

        except Exception, e:
            print 'boo, exception', str(e)
            return


# server = client.WebSocketClient(server_host = HOST, log_level='info',
#                                 origin = 'http://' + HOST,
#                                 server_port = int(PORT),
#                                 resource = SESSION_ID + '/do')

server = client.WebSocketClient(server_host = HOST, server_port = int(PORT),
                                log_level   = 'info',
                                origin      = 'http://' + HOST,
                                resource = "/do",
                                draft75=True)

server.func = web_socket_receive_data
thread = thread.start_new_thread(server.run, ())
