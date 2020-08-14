from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from time import sleep
import time
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import WebDriverException
import argparse
from functools import partial
from multiprocessing import Pool
import sys
import os
import subprocess
from subprocess import *
import urllib.request
import json
import re
import fcntl
import random
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from concurrent.futures import TimeoutError
from pebble import ProcessPool, ProcessExpired, ThreadPool

import concurrent.futures

# globals
EROOR_CHUNKS = []
FATAL_URL = []


def restartChrome():

    myurl = "http://172.17.0.1:8899/"
    try:
        resp = urllib.request.urlopen(myurl)
        if resp.getcode() == 200:
            return 1
        if resp.getcode() == 404:
            return 0
        else:
            raise Exception
    except Exception as e:
        print(e)


def sendTimeout(timeout_url):
    # sending timeout to http server manually because js obviously cant tell
    # the server it timed out
    myurl = "https://fpmon:8898/"
    body = '{"url":"' + timeout_url + '","coverage_entities":"","coverage_categories":"","aggressive_coverage":"", \
        "aggressive_categories":"","score":"","loadtime":"","TIMEOUT":"true","date":"","fingerprint_categories":"", \
        "fingerprint_categories_all":"","entities_all":"","script_origins_calls":""}'

    req = urllib.request.Request(myurl)
    jsondata = json.dumps(body)
    jsondataasbytes = jsondata.encode('utf-8')   # needs to be bytes

    req.add_header('Content-Type', 'application/json; charset=utf-8')
    req.add_header('Content-Length', len(jsondataasbytes))

    try:
        response = urllib.request.urlopen(req, jsondataasbytes)
    except TimeoutError as err:
        print("sendtimeout(): ", err)
    except Exception as err:
        print("sendtimeout() EXCEPTION: ", err)


def format_url(urls):
    return_urls = []
    bad_urls = []

    for url in urls:
        # only lowercase
        url = url.lower()

        # edgecase
        if "mailto" in url:
            bad_urls.append(url)
            continue

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

    if len(bad_urls) > 0:
        print("[+] Bad URLs found:", bad_urls)
    print("[+] Found: " + str(len(return_urls)) + " urls!")
    return return_urls


def read_file(filename):
    with open(filename) as file:
        return file.read().splitlines()


def divide_chunks(l, n):
    # looping till length l
    for i in range(0, len(l), n):
        yield l[i:i + n]


def add_to_redo_queue(url,protocol,counter):
    if url == None:
        print("something is wrong!!!!!")
        return

    if url.startswith("https:", 0, 6):
        url = url.replace("https://", protocol)

    global EROOR_CHUNKS

    # check if already exists
    if url in EROOR_CHUNKS:
        print("url already in errorchunks: " + url)
        return

    EROOR_CHUNKS.append(url)
    #print("["+str(counter)+"] Added to requeue: " ,url)
    print("[+] Added to requeue: " ,url)
    

def run(url):
    #url = "https://example.com"
    # sleep(random.randint(1,3))
    chrome_options = webdriver.ChromeOptions()
    # chrome_options.add_argument("--headless")
    # chrome_options.add_argument("--window-size=1920,1080");
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    chrome_options.add_argument("--load-extension=/chrome_app")
    #chrome_options.add_argument('--load-extension=/chrome_app,/ext/adblock/gighmmpiobklfepjocnamgkkbiglidom/4.8.0_0')
    #chrome_options.add_argument('--load-extension=/chrome_app,/ext/duckduckgo/bkdgflcldnnnapblkhphbgpggdiikppg/2019.12.12_0')
    #chrome_options.add_argument('--load-extension=/chrome_app,/ext/privacy_badger/pkehgijcmpdhfbdbbnkijodmdjhbjlgp/2020.2.19_0')
    err_url = 'dummy'

    try:
        # https://selenium-python.readthedocs.io/getting-started.html#using-selenium-with-remote-webdriver
        # https://medium.com/@zvisno/running-selenium-tests-with-docker-a484186cd3d
        driver = webdriver.Remote(command_executor='http://hub:4444/wd/hub',
                                  desired_capabilities=chrome_options.to_capabilities())
        time.sleep(1)

        driver.set_page_load_timeout(45)
        hard_timeout = 45
        # driver.implicitly_wait(30)
        driver.get(url)

        # wait for timeout
        counter = 0
        while (counter < hard_timeout):
            # mb redundant - timeout if driver timeout not works
            # if counter >= hard_timeout:
            #   raise TimeoutException('fpmon_success not found -> TIMEOUT')
            #   break
            try:
                # check for success <div>
                if driver.find_element_by_id('fpmon_success'):
                    # if found: everything worked as expected
                    # sleep(1)
                    break

            except NoSuchElementException:
                pass

            try:
                # check for errors like 404, cant resolve, page not found, etc...
                # if default errorpage of chromium is loaded -> don't wait full
                # timeout
                if driver.find_element_by_id('error-information-popup-container'):
                    #print("[?] Landed on default errorpage: " + url)
                    raise TimeoutException('error-information-popup-container')
                    break

            except NoSuchElementException:
                pass

            sleep(1)
            counter += 1

        if counter >= hard_timeout:
            raise TimeoutException('fpmon_success not found -> TIMEOUT')
    
    except TimeoutException:
        print("Timeout: " + url)
        sendTimeout(url)

        err_url = url

    except Exception as e:
        print(e)
        sendTimeout(url)
        err_url = "EXCEPTION|"+url
        #err_url = url

    finally:
        driver.quit()
    if err_url != 'dummy':
        return err_url
    else:
        return 0


def main(start_time):

    print("""
###############################################
# fpmon domain crawler #                      #
########################                      #
#                                             #
# -i urls.txt   # input urls                  #
# -y            # Linkdepth default: false    #
# -t 2          # threads                     #
# -d amazon.com # domain to crawl for links   #
# -r            # remove tmp data before start#
###############################################
""")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-d', '--domain', help='Enter domain for crawling like : "amazon.com"')
    parser.add_argument('-i', '--urls', help='url file')
    parser.add_argument('-y', '--linkdepth',
                        action='store_true', help='enabling linkdepth 1')
    parser.add_argument('-t', '--threads', default=1, help='threads')
    parser.add_argument('-r', '--remove', action='store_true',
                        help='clean temp data on the way')

    args = parser.parse_args()

    url_file = ''

    if args.urls:
        url_file = args.urls
        if args.remove:
            if os.path.exists("/monitor/out/crawl.csv"):
                os.remove("../monitor/out/crawl.csv")
                print("[-] removing /monitor/out/crawl.csv")

        # if file with urls is provided
        try:
            urls = read_file(args.urls)
            if args.linkdepth is True:
                print("LINKDEPTH to be implemented...")
                exit(1)
                # for item in urls:
                #     if item is not None:
                #         lynxCrawl(item,"append")
                # urls = read_file(l1)
            else:
                print("[+] Formatting input URLs!")
                urls = format_url(urls)

        except FileNotFoundError as err:
            sys.exit(err)
    else:
        print("[?] Please set a URL file for input!")
        exit(1)

    try:
        max_processes = int(args.threads)
    except ValueError as err:
        sys.exit(err)

    # To have a progress bar we divide input into chunks
    # TODO: 5% chunks

    #chunk_batch = len(urls)
    chunk_batch = 100
    chunk_size = 1
    TIMEOUT = 60

    x = list(divide_chunks(urls, chunk_batch))

    chunk_counter = 0
    print("[+] Scanning")
    t_counter = 0
    for chunks in x:
        
        try:
            # https://pythonhosted.org/Pebble/#processes
            # https://stackoverflow.com/questions/44402085/multiprocessing-map-over-list-killing-processes-that-stall-above-timeout-limi
            # multiprocessing levenshein distance
            # https://stackoverflow.com/questions/38271547/when-should-we-call-multiprocessing-pool-join
        
            with ProcessPool(max_workers=max_processes) as pool:
                future = pool.map(run, chunks, chunksize=chunk_size, timeout=TIMEOUT)

                iterator = future.result()
                counter = 0
                t_counter = 0

                while True:
                    try:
                        result = next(iterator)
                        if result != 0:
                            # handle exceptions and redo them
                            if result.startswith("EXCEPTION|", 0, 10):
                                result = result.replace("EXCEPTION|", "")
                                add_to_redo_queue(result, "https://", counter)
                            # try again with http
                            elif result.startswith("https:", 0, 6):
                                add_to_redo_queue(result, "http://", counter)
                        # else:
                        #   print("["+str(counter)+"] " + chunks[counter])
                    except StopIteration:
                        print("Stopping...")
                        break
                    except TimeoutError as error:
                        print("[ERR] Process TIMEOUT after "+str(TIMEOUT)+" seconds from url: " + chunks[counter])
                        add_to_redo_queue(chunks[counter], "http://", counter)
                        t_counter = 1
                            
                    except ProcessExpired as error:
                        print("%s. Exit code: %d" % (error, error.exitcode))
                        add_to_redo_queue(chunks[counter], "https://", counter)
                        t_counter = 1
                    except Exception as error:
                        print("function raised %s" % error)
                        # Python's traceback of remote process
                        # print(error.traceback)
                        add_to_redo_queue(chunks[counter], "https://" , counter)
                        t_counter = 1

                    counter += 1
                # mb sleep removable
                sleep(1)

            print("\nFinished chunk after %.2f seconds ---" %
                  (time.time() - start_time))
            #print("[+] Current err chunks: ", EROOR_CHUNKS)
            print("[+] Redo queue count: ", len(EROOR_CHUNKS))
            chunk_counter += 1

        except Exception as error:
            print("POOL ERROR %s" % error)
            # Python's traceback of remote process
            print(error.traceback)

        print("[+] Scanning chunk progress: " +
              str(chunk_counter * len(chunks)) + "/" + str(len(urls)))
        
        # restart chromes after deadlock occures (and try a second time)
        if t_counter:
            if restartChrome() == 1:
                print("Restarted all Chromes nodes successfully!!!")
            else:
                print("Error at restarting Chromes!")
                print("trying again...")
                if restartChrome() == 1:
                    print("Restarted all Chromes nodes successfully after second try!!!")
                else:
                    exit(1)


    if EROOR_CHUNKS != []:
        print("[+] Scanning EROOR_CHUNKS")
        print(EROOR_CHUNKS)
        chunk_batch = 14
        x2 = list(divide_chunks(EROOR_CHUNKS, chunk_batch))
        chunk_counter = 0

        for echunks in x2:
            
            try:
                # https://pythonhosted.org/Pebble/#processes
                # https://stackoverflow.com/questions/44402085/multiprocessing-map-over-list-killing-processes-that-stall-above-timeout-limi
                # multiprocessing levenshein distance
                # https://stackoverflow.com/questions/38271547/when-should-we-call-multiprocessing-pool-join
            
                with ProcessPool(max_workers=max_processes) as pool:
                    future = pool.map(run, echunks, chunksize=chunk_size, timeout=TIMEOUT)

                    iterator = future.result()
                    counter = 0
                    t_counter = 0

                    while True:
                        try:
                            result = next(iterator)
                            # if result != 0:
                            #   print("Timeout: ", echunks[counter])
                            # else:
                            #   print("["+str(counter)+"] " + echunks[counter])
                        except StopIteration:
                            print("Stopping...")
                            break
                        except TimeoutError as error:
                            print("[ERR] Process TIMEOUT after "+str(TIMEOUT)+" seconds from url: " + echunks[counter])
                            t_counter = 1   
                        except ProcessExpired as error:
                            print("%s. Exit code: %d" % (error, error.exitcode))
                            t_counter = 1
                        except Exception as error:
                            print("function raised %s" % error)
                            # Python's traceback of remote process
                            print(error.traceback)
                            t_counter = 1
                            

                        counter += 1
                    # mb sleep removable
                    sleep(1)

                print("\nFinished EROOR_CHUNKS after %.2f seconds ---" %
                      (time.time() - start_time))
                chunk_counter += 1

            except Exception as error:
                print("POOL ERROR %s" % error)
                # Python's traceback of remote process
                print(error.traceback)

            print("[+] Scanning chunk progress: " +
                  str(chunk_counter * len(echunks)) + "/" + str(len(EROOR_CHUNKS)))
            
            # restart chromes after deadlock occures (and try a second time)
            if t_counter:
                if restartChrome() == 1:
                    print("Restarted all Chromes nodes successfully!!!")
                else:
                    print("Error at restarting Chromes!")
                    print("trying again...")
                    if restartChrome() == 1:
                        print("Restarted all Chromes nodes successfully after second try!!!")
                    else:
                        exit(1)
    # # working on errorchunks
    # chunk_counter = 0
    # global FATAL_URL

    # try:

    #   if EROOR_CHUNKS != []:
    #       print("[+] Scanning EROOR_CHUNKS")
    #       print(EROOR_CHUNKS)

    #       with ProcessPool(max_workers=max_processes) as pool:
    #           future = pool.map(run, EROOR_CHUNKS, chunksize=chunk_size, timeout=TIMEOUT)

    #           iterator = future.result()
    #           counter = 0

    #           while True:
    #               try:
    #                   result = next(iterator)
    #                   if result != 0:
    #                       FATAL_URL.append(result)
    #                       print("[+] Added to FATAL_URL: ", result)
    #                   else:
    #                       print("["+str(counter)+"] " + EROOR_CHUNKS[counter])
    #               except StopIteration:
    #                   print("STOP")
    #                   break
    #               except TimeoutError as error:
    #                   # print("function took longer than %d seconds" % error.args[0])
    #                   print("Process TIMEOUT after "+str(TIMEOUT)+" seconds from url: " +
    #                         EROOR_CHUNKS[counter])
    #                   FATAL_URL.append(EROOR_CHUNKS[counter])
    #                   print("[+] Added to FATAL_URL: ", EROOR_CHUNKS[counter])
    #               except ProcessExpired as error:
    #                   print("%s. Exit code: %d" % (error, error.exitcode))
    #                   FATAL_URL.append(EROOR_CHUNKS[counter])
    #                   print("[+] Added to FATAL_URL: ", EROOR_CHUNKS[counter])
    #               except Exception as error:
    #                   print("function raised %s" % error)
    #                   print(error.traceback)  # Python's traceback of remote process
    #                   FATAL_URL.append(EROOR_CHUNKS[counter])
    #                   print("[+] Added to FATAL_URL: ", EROOR_CHUNKS[counter])
    #               sleep(1)
    #               counter += 1

    #       print("\nFinished EROOR_CHUNKS after %.2f seconds ---" %
    #             (time.time() - start_time))
    #       print("[+] FATAL_URL = timeouts only: ")
    #       print(FATAL_URL)

    # except Exception as error:
    #   print("POOL ERROR %s" % error)
    #   # Python's traceback of remote process
    #   print(error.traceback)



if __name__ == '__main__':
    start_time = time.time()
    main(start_time)
    print("--- Complete after %.2f seconds ---" % (time.time() - start_time))
