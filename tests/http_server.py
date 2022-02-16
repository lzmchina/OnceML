from http.server import HTTPServer, BaseHTTPRequestHandler, ThreadingHTTPServer
import time
from typing import Counter, Tuple
from threading import Thread
import signal
from onceml.templates.ModelGenerator import ModelGenerator
import onceml.utils.logger as oncemllogger
from onceml.utils.logger import logger
import logging
import queue
logger.info("dsdd")
server=None
def shutdownFunction(signalnum, frame):
    print('You pressed Ctrl+C!')
    print(server)
    server.shutdown

import sys

logging.error("ddd")
def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    


for sig in [signal.SIGINT, signal.SIGTERM]:
    print(sig)
    signal.signal(sig, shutdownFunction)

class myHandler(BaseHTTPRequestHandler):
    #Handler for the GET requests
    count = 0

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Uri', self.path)
        self.end_headers()
        self.wfile.write("hi multi threading test {}!\n".format(
            myHandler.count).encode("utf-8"))
        myHandler.count += 1
        Thread(target=time.sleep, args=(10, )).start()
        raise Exception
        print("xdxdx")


PORT_NUM = 10087
serverAddress = ("0.0.0.0", PORT_NUM)
server = ThreadingHTTPServer(serverAddress, myHandler)
Thread(target=server.serve_forever, args=(10, )).start()