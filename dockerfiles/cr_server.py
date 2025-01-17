#!/usr/bin/env python3
"""
Very simple HTTP server in python for logging requests
Usage::
	./server.py [<port>]
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import json
import csv
import os
import ssl
import hashlib
ssl._create_default_https_context = ssl._create_unverified_context
import subprocess
from subprocess import *
from time import sleep


def print_banner():
	print("""
#########################################
# fpmon Chrome Restart server #         #
###############################         #
#                                       #
# Very simple HTTP server in python for #
# logging requests                      #
#                                       #
# ./server.py [<port>]                  #
#########################################
""")

def docker_compose():
	bashCommand = "/usr/bin/docker-compose restart hub chrome"
	#bashCommand = "/usr/bin/docker-compose -v"

	try:
		process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
		output, error = process.communicate()
		print(output)
	
	except Exception as error:
		print(error)
		return 0

	print("successfullt restarted chromes")
	print("wait for connection to hub")
	sleep(15)
	return 1



class S(BaseHTTPRequestHandler):
	def _set_response(self):
		if docker_compose():
			self.send_response(200)
			self.send_header('Content-type', 'text/html')
			self.end_headers()
		else:
			self.send_response(404)
			self.send_header('Content-type', 'text/html')
			self.end_headers()


	def do_GET(self):
		logging.info("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
	
		self._set_response()
		self.wfile.write("GET request for {}".format(self.path).encode('utf-8'))


	# def do_POST(self):
	#     content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
	#     post_data = (self.rfile.read(content_length)).decode('utf-8') # <--- Gets the data itself
	#     #logging.info("POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n",
	#     #        str(self.path), str(self.headers), post_data.decode('utf-8'))
	#     try:
	#         post_data = json.loads(post_data)
	#     except Exception as err:
	#         print("JSON:",err)
	#     parse_csv(post_data)

	#     #domain = post_data.split(".", 2)[1]
	#     #logging.info("Incoming POST request writing to csv")
	#     #logging.info(post_data.decode('utf-8'))
		
	#     self._set_response()
	#     self.wfile.write("POST request for {}".format(self.path).encode('utf-8'))


def run(server_class=HTTPServer, handler_class=S, port=8899):
	logging.basicConfig(level=logging.INFO)
	server_address = ('', port)
	httpd = server_class(server_address, handler_class)
	#httpd.socket = ssl.wrap_socket(httpd.socket, certfile='../monitor/key.pem', server_side=True)
	logging.info('Starting httpd...\n')
	try:
		httpd.serve_forever()
	except KeyboardInterrupt:
		pass
	httpd.server_close()
	logging.info('Stopping httpd...\n')

if __name__ == '__main__':
	from sys import argv
	print_banner()

	if len(argv) == 2:
		run(port=int(argv[1]))
	else:
		run()
