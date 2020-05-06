#!/usr/bin/python3
import requests
from bs4 import BeautifulSoup
import pymongo
import argparse
import re
from os import path, makedirs

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
                        , help="run the program with more prints(debug mode)")
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

    #We only want the tld and domain to serve as the collection name
    url = url.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
    if url in db.collection_names() and debug:
        print("[DEBUG]" + url + " is already in our database, we will check for changes and update if there's any.")
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
        print("[DEBUG] List of firmwares found(brand, model, title, stock_rom, android_version, author, last_modified, rockchip_chipset): ")        

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
        for item in items[1:]:#items[0] is the titles of the table
            brand = find_by_view_field(item, 'views-field views-field-field-brand')
            model = find_by_view_field(item, 'views-field views-field-field-model')
            title = find_by_view_field(item, 'views-field views-field-title')
            stock_rom = find_by_view_field(item, 'views-field views-field-field-stock-rom')
            android_version = find_by_view_field(item, 'views-field views-field-field-android-version2')
            author = find_by_view_field(item, 'views-field views-field-field-firmware-author')

            #Collect more metadata from it's page(last modified date, rockchip_chipset and the download link)
            item_url = item.findAll('td', {'class': 'views-field views-field-title'})[0].find('a').attrs['href'].replace('\\', '/')
            data = requests.get(base_url + item_url).content
            soup = BeautifulSoup(data, "lxml")

            last_modified = find_by_view_field(soup, 'field field-name-changed-date field-type-ds field-label-inline clearfix', 'div')
            rockchip_chipset = find_by_view_field(soup, 'field field-name-field-chipset field-type-taxonomy-term-reference field-label-inline clearfix' \
                                                    , 'div')
            download_url = soup.find('a', {'href':re.compile('(.*\.zip|.*\.rar)')})

            last_modified  = re.sub(".*:[^,]*, ", "", last_modified, count=1)#Remove the "Last Modified:" and day of the week
            rockchip_chipset = re.sub(".*:.?", "", rockchip_chipset)#Remove the "Rockchip Chipset:"    
            if download_url != None:
                download_url = download_url.attrs['href']
            else:
                download_url = ""

            if debug:
                print("[DEBUG] >> " + ", ".join([brand, model, title, stock_rom, android_version, author, last_modified, rockchip_chipset]))

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
                        "last_modified" : last_modified,
                        "rockchip_chipset" : rockchip_chipset,
                        "download_url" : download_url
                    }
                },
                upsert=True
            )

def find_by_view_field(item, view_field, tag='td'):
    """
    This function finds view_field in item and formats it(removes unnecessary spaces and new-lines)
    @param0: item - the item that we want to find the view_field in
    @param1: view_field - the view filed we want to find
    @param2: tag - defaults to 'td', the tag that we want to find the view_field in
    @return: formated text of the view_field
    """
    field = item.find(type, {'class': view_field})
    if field != None:
        return re.sub("^\s+|\s+$", "", field.text)
    else:
        return ""


def get_firmwares_download_link(db, debug):
    """
    This funciton will access the database and retrive the urls of the firmwares to download
    @param0: db - object of collections, used to get the url of the firmwares(they are stored in the database when we crawl the metadata) 
    @param1: debug - is the progam running in debug mode
    @return:
    """
    urls = list()#A list to save urls to
    if debug:
        print("[DEBUG] Fetching links for downloading firmwares")

    for firmware in db.find():
        #Save the download link
        if firmware['download_url'] != "":
            urls.append(firmware['download_url'])
        elif debug:
            print("[DEBUG] No download link found for " + firmware['title'])

    return urls

def download_firmwares(urls, save_location, debug):
    """
    This funciton will download the firmwares from a given list of urls
    @param0: urls - list of urls to download the firmwares from
    @param1: save_location - the folder in which the firmwars are downloaded to
    @param2: debug - is the progam running in debug mode
    @return: None
    """
    #Download the firmwars from the urls
    print("Starting to download the firmwares.")

    #If we don't save the file to a directory by any chance(maybe user froget to add /)
    if "/" not in save_location:
        save_location = save_location + "/"
    
    #Create the directory in which we save the file if it doesn't exsits
    if path.isdir(save_location) is False:
        makedirs(save_location)#makedirs to allow a folder inside of a folder

    for index, url in enumerate(urls):
        filename = save_location + url.split("/")[-1]
        #Use stream to get the data as chunks
        with requests.get(url, stream=True) as r, open(filename, "wb") as f:
            try:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            except:
                if debug:
                    print("[DEBUG] error occurred while downloading " + filename)

            if debug:
                print("[DEBUG] " + filename + " was downloaded successfully!")

        #Print progress message every ~5%
        if int(len(urls) / 20) == index:
            print("Finished {:.2f}% of the download.".format((index / len(urls)) * 100))    

def main():
    #Init the parser
    parser = init_parser()
    args = parser.parse_args()
    debug = args.debug
    if debug:
        print("[DEBUG] The args of the program are: " + str(args))
    #Fix an issue when the link provided to the program is in wrong format, the website redirects to home page if there's no www
    if 'www' not in args.url:
        args.url = args.url.replace("https://", "https://www.").replace("http://", "http://www.")
    print("Crawling the website " + args.url + " for firmwares.")

    #Init the database
    db = init_db(args.dbserver, args.dbname, args.url, debug)

    #Get the link to the downloads page
    downloads_url = get_downloads_page_url(args.url, args.debug)
    if debug:
        print("[DEBUG] The url where downloads are located is: " + downloads_url)

    #Get the metadata of all firmwares
    crawl_metadata(args.url, downloads_url, db, args.debug)

    #Download all of the firmwares
    urls = get_firmwares_download_link(db, args.debug)
    download_firmwares(urls, args.folder, args.debug)

    print("Finished downloading all of the available firmwares.")

if __name__ == "__main__":
    main()
