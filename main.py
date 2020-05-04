#!/usr/bin/python3
import requests
from bs4 import BeautifulSoup
import pymongo
import argparse

def init_parser():
    """
    This function creates the parser of args that are given to the program
    @return: inited argument parser
    """
    parser = argparse.ArgumentParser(description="Firmware web crawler")
    parser.add_argument("-dbs", "--dbserver", default="mongodb://localhost:27017/"
                        , help="specify a mongodb server address to save results to(defualt is mongodb://localhost:27017/)")
    parser.add_argument("-dbn", "--dbname", default="firmware_database"
                        , help="specify a database to save results to(defualt is firmware_database)")
    parser.add_argument("-d", "--debug", action="store_true"
                        , help="run the program with more prints")
    parser.add_argument("url", help="specify the url of the site you want to crawl firmware from")
    return parser

def init_db(db_server, db_name, url, debug):
    """
    This function connects to the database
    @param0: db_server - the address of the server
    @param1: db_name - the name of the database where we going to store the collections with the firmware info
    @param2: url - the url of the site we want to crawl
    @param3: debug - is the progam running in debug mode
    @return: a collection that we can add the information that we gather to
    """
    db_client = pymongo.MongoClient(db_server)
    db = db_client[db_name]

    #We only want the tld part of the domain to serve as the collection name
    url = url.replace("https://", "")
    url = url.split("/")[0]
    if url in db.collection_names():
        print(url + " is already in our database, we will check for changes in it.")
    collection = db[url]

    if debug:
        print("[DEBUG] Created " + url + " collection in " + db_name + " database (mongodb server: " + db_server + ")")
    return collection

def get_downloads_page_url(url, debug):
    """
    This function crawles the given url to find the the page which contains the firmwares
    @param0: url - the url we look in for the download page, might be the download page
    @param1: debug - is the progam running in debug mode
    @return: url of the page which contains the firmwares
    """
    data = requests.get(url).content
    soup = BeautifulSoup(data, "lxml")
    links = soup.findAll('a', {'title': "Download"})

    if debug and len(links) > 1:
        print("[DEBUG] Found more then one link to download page, preceding with the first.")

    if len(links) == 0:
        print("Found no links to download page, assuming that the given url is the download page.")
        return url

    return url + links[0].attrs['href']

def main():
    #Init the parser
    parser = init_parser()
    args = parser.parse_args()
    debug = args.debug
    if debug:
        print("[DEBUG] The args of the program are: " + str(args))

    #Init the database
    db = init_db(args.dbserver, args.dbname, args.url, debug)

    #Get the link to the downloads page
    downloads_url = get_downloads_page_url(args.url, args.debug)
    if debug:
        print("[DEBUG] The url where downloads are located is: " + downloads_url)

if __name__ == "__main__":
    main()
