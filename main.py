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
    parser.add_argument("-f", "--folder", default="firmwares/"
                        , help="specify a location to save firmwares to(defualt is firmwares/)")                 
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
    link = soup.find('a', {'title': "Download"})

    #Fix an issue when the link provided to the program is in wrong format, the website redirects to home page if there's no www
    if 'www' not in url:
        url = url.replace("https://", "https://www.")

    if link == None:
        print("Found no links to download page, assuming that the given url is the download page.")
        return url

    return url + link.attrs['href']

def crawl_metadata(base_url, downloads_url, db, debug):
    """
    This function crawls the metadata of all available firmwares from the downloads pages and puts them into the database 
    @param0: url - the url of the downloads pages
    @param1: db - object of collections, we will put the metadata that we find into it
    @param2: debug - is the progam running in debug mode
    @return: None
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
            item_url = current.findAll('td', {'class': 'views-field views-field-title'})[0].find('a').attrs['href'].replace('\\', '/')

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

def download_firmwares(db, base_url, save_location, debug):
    """
    This funciton will access the database, retrive the urls of the firmwares to download and download them
    @param0: db - object of collections, used to get the url of the firmwares(they are stored in the database when we crawl the metadata) 
    @param1: base_url - the url of the website(will append the url of the firmware to it)
    @param2: save_location - the folder in which the firmwars are downloaded to
    @param3: debug - is the progam running in debug mode
    @return: None
    """
    for current in db.find():
        print(base_url + current['url'])
        data = requests.get(base_url + current['url']).content
        soup = BeautifulSoup(data, "lxml")

        #Find the tag that holds the download link
        download_link = soup.find('a', {"type": re.compile("application\/zip*")})

        #There's some pages with other download link location
        if download_link == None:
            download_link = soup.find('div', 
                {"class": "field field-name-field-firmware-image-download field-type-text field-label-above"})

            #There's some pages with no link at all
            if download_link != None:
                download_link = download_link.find('a')
        if download_link != None:
            print(download_link.attrs['href'])
        else:
            print("None")

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

    #Get the metadata of all firmwares
    crawl_metadata(args.url, downloads_url, db, args.debug)

    #Download all of the firmwares
    download_firmwares(db, args.url, args.folder, args.debug)

if __name__ == "__main__":
    main()
