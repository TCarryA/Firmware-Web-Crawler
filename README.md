# Firmware-Web-Crawler
## Usage:
```
main.py [-h] [-dbs DBSERVER] [-dbn DBNAME] [-f FOLDER] [-d] [-F] url

Firmware web crawler

positional arguments:
  url                   specify the url of the site you want to crawl firmware
                        from

optional arguments:
  -h, --help            show this help message and exit
  -dbs DBSERVER, --dbserver DBSERVER
                        specify a mongodb server address to save results
                        to(defualt is mongodb://localhost:27017/)
  -dbn DBNAME, --dbname DBNAME
                        specify a database to save results to(defualt is
                        firmware_database)
  -f FOLDER, --folder FOLDER
                        specify a location to save firmwares to(defualt is
                        firmwares/)
  -d, --debug           run the program with more prints(debug mode)
  -F, --force           force downloading the files even if they are up to
                        date
examples:

 python3 main.py https://rockchipfirmware.com/
 python3 main.py -d https://rockchipfirmware.com/
 python3 main.py -F -d https://rockchipfirmware.com/
  ```
  This script was tested for https://www.rockchipfirmware.com/ .
