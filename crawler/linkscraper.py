import itertools
import time
import argparse

import sys
import os
from pebble import ProcessPool, ProcessExpired, ThreadPool

import requests
from bs4 import BeautifulSoup

import re

#import urllib
import lxml.html
import urllib.parse

from urllib.request import urlopen
from subprocess import Popen, PIPE
import subprocess
from subprocess import *

def read_file(filename):
    with open(filename) as file:
        #return file.readlines()
        content = list(file)
        for item in range(len(content)):
            if content[item].endswith("\n"):
                content[item] = content[item][:-1]
        return content

def format_url(urls):
    return_urls = []
    bad_urls = []

    for url in urls:
        # only lowercase
        url = url.lower()

        # "https" is good
        if url.startswith("https://"):
            return_urls.append(url)
            continue

        # "http" is good
        if url.startswith("http://"):
            return_urls.append(url)
            continue

        # if not formatted at all
        return_urls.append("https://" + url)
        #return_urls.append("http://" + url)

    return return_urls


def parse_anwsers(data,domain):
    parsed = []
    try:
        for item in range(len(data)-1):
            # delete \n
            newitem = data[item].decode('utf-8', 'ignore')
            if "http" in newitem:
                #parsed.append(newitem.rsplit(" ",1)[1][:-1])
                url = newitem.rsplit(" ",1)[1].replace("\n","")
                
                base = url.split("//")[1]
                
                dom = domain.split("//",1)[1]
                if "/" in dom:
                    dom = dom.split("/",1)[0]
                domvs = base.split("/",1)[0]
                if domvs == dom or domvs.endswith("."+dom):
                    parsed.append(url)
                
    except Exception as exc:
        print(exc)

    return list(set(parsed))

def run(url):
    collected = []
    #print("URL: ", url)
    try:
        #cmd4 = "/usr/bin/lynx -listonly -dump -unique_urls -accept_all_cookies -connect_timeout=10 -useragent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36' {} ".format(
        #    url)
        cmd4 = "/usr/bin/lynx -listonly -dump -unique_urls -accept_all_cookies -connect_timeout=10 '{}' ".format(
            url)

        #print(cmd)
        # output = Popen(cmd4,stdout=PIPE)
        # response = output.communicate()
        #print(response)
        try:
            sp = subprocess.Popen(['/bin/bash', '-c', cmd4], stdout=subprocess.PIPE)
            answer = sp.stdout.readlines()
            #print(answer)
            answer2 = parse_anwsers(answer,url)
            answer2.sort()
            # print(answer2)
            # for item in answer2:
            #     print(item)

            return answer2

        except Exception as err:
            print(err)
            #print("lynxCrawl()")

    except Exception as exc:
        print(exc)
        #print("RUN()")

def main(start_time):

    print("""
###############################################
# Directory Collector        #                #
##############################                #
#                                             #
# -l 1    # linkdepth      1-x                #
###############################################
""")

    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--domain', default='domain.txt',help='length of name')
    parser.add_argument('-o', '--out', default='out.txt',help='output')
    parser.add_argument('-t', '--threads', default=1, help='threads')
    parser.add_argument('-r', '--remove', action='store_true',
                        help='clean temp data on the way')
    args = parser.parse_args()

    try:
        max_processes = int(args.threads)
    except ValueError as err:
        sys.exit(err)

    if args.out:
        output = args.out+"_tmp"
        output2 = args.out
    else :
        print("Need Path")
        exit(1)

    if args.remove:
        if os.path.exists(output):
            os.remove(output)
            print("[-] removing ", output)
        
        if os.path.exists(output2):
            os.remove(output2)
            print("[-] removing ", output2)

    voc = []
    if args.domain:
        voc = format_url(read_file(args.domain))
        print(voc)
    else:
        exit(1)

    chunk_size = 1
    all_url = []
    all_url.extend(voc)
    print("[+] Scanning")
    #print("Answer: ", run("https://twitter.com"))
    #exit(1)
    try:
        with ProcessPool(max_workers=max_processes) as pool:
            future = pool.map(run, voc, chunksize=chunk_size, timeout=10)

            iterator = future.result()
            counter = 0
            t_counter = 0

            while True:
                try:
                    result = next(iterator)
                    all_url.extend(result)
                    try:
                        #if result != "[]":
                        print(voc[counter] +" : " +str(len(result))+" : " +str(len(all_url)))
                        with open(output , "a") as file:
                            for results in result:
                                file.write(results+"\n")
                    except Exception as exc:
                        print(exc)
                except StopIteration:
                    print("Stopping...")
                    break
                except TimeoutError as error:
                    print("[ERR] TIMEOUT after "+str(TIMEOUT)+" seconds from url: " + voc[counter])
                except ProcessExpired as error:
                    print("%s. Exit code: %d" % (error, error.exitcode))
                except Exception as error:
                    print("function raised %s" % error)
                    #print(error.traceback)
               # time.sleep(1)
                counter += 1

        print("\nFinished chunk after %.2f seconds ---" %
              (time.time() - start_time))

    except Exception as error:
        print("POOL ERROR %s" % error)
        # Python's traceback of remote process
        #print(error.traceback)
      
    all_url.extend(read_file(output))
    all_url = list(set(all_url))
    all_url.sort()
    print("Found : ", len(all_url), output2)
    with open(output2 , "a") as file:
        for items in all_url:
            if items.startswith("http://") or items.startswith("https://"):
                file.write(items+"\n")
    # cleanup
    if os.path.exists(output):
        os.remove(output)
        print("[-] removing ", output)

if __name__ == '__main__':
    start_time = time.time()
    main(start_time)
    print("--- Complete after %.2f seconds ---" % (time.time() - start_time))
