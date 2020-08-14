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


def checkLastByte(data):
    if data == "":
        return ""
    if data[-1] != ";":
        pass
    else:
        #print("replacing: ;")
        data = data[:-1]
    return data

def reduceCat(uniquecats, fullcats):
    if (uniquecats == "") or (fullcats == ""):
        return ""

    uniquecats = checkLastByte(uniquecats)
    fullcats = checkLastByte(fullcats)

    uniquecats = uniquecats.split(";")
    fullcats = fullcats.split(";")

    score = len(uniquecats)
    sequence_cats = []
    nexte = ""
    for i in range(0, len(fullcats)): # iterate full signature
        e = fullcats[i]
        if(i+1 < len(fullcats)):
            nexte = fullcats[i+1]
            sequence_cats.append(e) # append to sequence signature
        if(e in uniquecats):
            uniquecats.remove(e) # remove from unique if found 
        if(len(uniquecats) == 0): # if unique is empty -> we found every element at least once
            if(nexte != e): # add til next element is different (this makes a difference!)
                break;

    return ";".join(sequence_cats)

def print_banner():
    print("""
#########################################
# fpmon http server #                   #
#####################                   #
#                                       #
# Very simple HTTP server in python for #
# logging requests                      #
#                                       #
# ./server.py [<port>]                  #
#########################################
""")

def parse_csv(data):
    jsondata = ""
    if data:
        try:
            jsondata = json.loads(data)
        except Exception as err:
            print("J:",err)
            print(data)

    jsonfile = "tmp.csv"

    # if there is a file existing -> skip
    if os.path.exists(jsonfile) and os.path.getsize(jsonfile) > 0:
        pass
    else: 
        # if there is no file; create one and add CSV header
        f = open(jsonfile, "w", newline='')
        writer = csv.writer(f)
        writer.writerow(["url", "coverage_entities","coverage_categories",
            "aggressive_coverage","aggressive_categories", "score","enitity_hash","loadtime","TIMEOUT","date",
            "fingerprint_categories","fingerprint_categories_all","entities_all", "script_origins_calls"])
        f.close()

    reducedCats = reduceCat(jsondata["fingerprint_categories"], jsondata["fingerprint_categories_all"])
    #print(reducedCats)
    # just append new content
    f = open(jsonfile, "a", newline='')
    writer = csv.writer(f)

    try:
        # write content
        print("url:      " + jsondata["url"])
        print("score:    " + jsondata["score"])
        print("loadtime: " + jsondata["loadtime"])
        print("timeout:  " + jsondata["TIMEOUT"])

        writer.writerow([jsondata["url"],
                jsondata["coverage_entities"],
                jsondata["coverage_categories"],
                jsondata["aggressive_coverage"],
                jsondata["aggressive_categories"],
                jsondata["score"],
                hashlib.md5(jsondata["entities_all"].encode('utf-8')).hexdigest(),
                jsondata["loadtime"],
                jsondata["TIMEOUT"],
                jsondata["date"],
                jsondata["fingerprint_categories"],
                #jsondata["fingerprint_categories_all"],
                reducedCats,
                jsondata["entities_all"],
                jsondata["script_origins_calls"]])
    
    except Exception as e:
        print(e)

    f.close()

class S(BaseHTTPRequestHandler):
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    # def do_GET(self):
    #     logging.info("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
    #     self._set_response()
    #     self.wfile.write("GET request for {}".format(self.path).encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
        post_data = (self.rfile.read(content_length)).decode('utf-8') # <--- Gets the data itself
        #logging.info("POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n",
        #        str(self.path), str(self.headers), post_data.decode('utf-8'))
        try:
            post_data = json.loads(post_data)
        except Exception as err:
            print("JSON:",err)
        parse_csv(post_data)

        #domain = post_data.split(".", 2)[1]
        #logging.info("Incoming POST request writing to csv")
        #logging.info(post_data.decode('utf-8'))
        
        self._set_response()
        self.wfile.write("POST request for {}".format(self.path).encode('utf-8'))


def run(server_class=HTTPServer, handler_class=S, port=8898):
    logging.basicConfig(level=logging.INFO)
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    httpd.socket = ssl.wrap_socket(httpd.socket, certfile='key.pem', server_side=True)
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
