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
    parser.add_argument("-dbs", "--dbserver"
                        , help="specify a different mongodb server to save results to(by defualt mongodb://localhost:27017/")
    parser.add_argument("url", help="specify the url of the site you want to crawl firmware from")
    return parser

def init_db(db_server):
    """
    This function connects to the database
    """

def main():
    #init the parser
    parser = init_parser()
    args = parser.parse_args()

    #init the database, if arg.dbserver is specified then connect to it, else connect to defualt server(mongodb://localhost:27017/)
    if args.dbserver:
        init_db(args.dbserver)
    else:
        init_db("mongodb://localhost:27017/")


if __name__ == "__main__":
    main()
