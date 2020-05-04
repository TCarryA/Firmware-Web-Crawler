#!/usr/bin/python3
import requests
from bs4 import BeautifulSoup
import pymongo
import argparse
import re

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
    url = url.replace("https://", "").replace("www.", "").split("/")[0]
    if url in db.collection_names():
        print(url + " is already in our database, we will check for changes and update if there's any.")
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

    #Fix an issue when the link provided to the program is in wrong format, the website redirects to home page if there's no www
    if 'www' not in url:
        url = url.replace("https://", "https://www.")

    if debug and len(links) > 1:
        print("[DEBUG] Found more then one link to download page, preceding with the first.")

    if len(links) == 0:
        print("Found no links to download page, assuming that the given url is the download page.")
        return url

    return url + links[0].attrs['href']

def crawl_metadata(base_url, downloads_url, db, debug):
    """
    This function crawls the metadata of all available firmwares from the downloads pages and puts them into the database 
    @param0: url - the url of the downloads pages
    @param1: db - object of collections, we will put the metadata that we find into it
    @param2: debug - is the progam running in debug mode
    """
    if debug:
        print("[DEBUG] List of firmwares found(brand, model, title, stock_rom, android_version, author ,url): ")        

    while True:
        data = requests.get(downloads_url).content
        soup = BeautifulSoup(data, "lxml")
        items = soup.findAll('table')[0].findAll('tr')#get the items inside the table
        
        #Check for next page, update it if theres next or quit if theres no further pages
        next = soup.findAll('a', {'title': "Go to next page"})#next page
        if len(next) == 0:
            break#exit the loop if there's no next
        downloads_url = base_url + next[0].attrs['href']

        #Parse the items and send them to the database
        for current in items[1:]:#items[0] is the titles of the table
            brand = find_by_view_field(current, 'views-field views-field-field-brand')
            model = find_by_view_field(current, 'views-field views-field-field-model')
            title = find_by_view_field(current, 'views-field views-field-title')
            stock_rom = find_by_view_field(current, 'views-field views-field-field-stock-rom')
            android_version = find_by_view_field(current, 'views-field views-field-field-android-version2')
            author = find_by_view_field(current, 'views-field views-field-field-firmware-author')
            item_url = current.findAll('td', {'class': 'views-field views-field-title'})[0].find('a').attrs['href']

            if debug:
                print("[DEBUG] >> " + ", ".join([brand, model, title, stock_rom, android_version, author, item_url]))

            db.update(
                {
                    "title" : title
                },
                { 
                    "$set":#title will be inserted automatically 
                    {
                        "brand" : brand,
                        "model" : model,
                        "stock_rom" : stock_rom,
                        "android_version" : android_version,
                        "author" : author,
                        "url" : item_url
                    }
                },
                upsert=True
            )

def find_by_view_field(item, view_field):
    """
    This function finds view_field in item and formats it(removes unnecessary spaces and new-lines)
    @param0: item - the item that we want to find the view_field in
    @param1: view_field - the view filed we want to find
    @return: formated text of the view_field
    """
    field = item.findAll('td', {'class': view_field})[0].text
    return re.sub("^\s+|\s+$", "", field)

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

    crawl_metadata(args.url, downloads_url, db, args.debug)

if __name__ == "__main__":
    main()
