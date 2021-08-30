
from http.server import HTTPServer,BaseHTTPRequestHandler,ThreadingHTTPServer
import time
from typing import Counter, Tuple
from threading import Thread
class myHandler(BaseHTTPRequestHandler):
    #Handler for the GET requests
    count=0
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.send_header('Uri',self.path)
        self.end_headers()
        self.wfile.write("hi multi threading test {}!\n".format(myHandler.count).encode("utf-8"))
        myHandler.count+=1
        Thread(target=time.sleep, args=(10,)).start()
        print("xdxdx")
PORT_NUM=8080
serverAddress=("0.0.0.0", PORT_NUM)
server=ThreadingHTTPServer(serverAddress, myHandler)
server.serve_forever()
