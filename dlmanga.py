#!/usr/bin/env python3
import requests
from html.parser import HTMLParser
import time
import urllib
import os
import json
import base64
import logging
import sys

logger = logging.getLogger('dlmanga')
fh = logging.FileHandler('dlmanga.log')
fh.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(fh)
logger.addHandler(ch)
logger.setLevel(logging.INFO)

url = 'https://manga.madokami.al'
mangaDir = '/mnt/RAID/Manga'

s = requests.Session()
s.auth = ('username', 'password')
r = s.get(url)
content = r.content
links = []
current_path = "";
jsonData = {}
totalSize = 0

class MyHTMLParser(HTMLParser):
    # TODO get related series
    def __init__(self):
        super().__init__()
        self.insideIndexTable = False
        self.insideTbody = False
        self.recordingGenre = False
        self.recordingTag = False
        self.recordingAuthor = False
        self.recordingYear = False
        self.recordingTitle = False
        self.recordingScanStatus = False

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            for attr in attrs:
                if attr[0] == 'id' and attr[1] == 'index-table':
                    self.insideIndexTable = True
        if tag == 'tbody':
            self.insideTbody = True
        if tag == 'a' and self.insideIndexTable and self.insideTbody:
            for attr in attrs:
                if (attr[0] == 'href' and
                        not attr[1].startswith('https://') and
                        attr[1] != '#' and
                        #attr[1] != '/Manga/_Autouploads' and
                        attr[1] != '/Manga/Non-English'):
                    links.append(attr[1])
        elif tag == 'a':
            for attr in attrs:
                if attr[0] == 'class' and attr[1] == 'tag':
                    #genres
                    self.recordingGenre = True
                elif attr[0] == 'class' and attr[1] == 'tag tag-category':
                    #tags
                    self.recordingTag = True
                elif attr[0] == 'itemprop' and attr[1] == 'author':
                    #author
                    self.recordingAuthor = True
                elif attr[0] == 'href' and attr[1].startswith('https://www.mangaupdates'):
                    #mangaupdates link
                    jsonData[current_path]["mangaUpdatesLink"] = attr[1]
        if tag == 'span':
            for attr in attrs:
                if attr[0] == 'class' and attr[1] == 'title':
                    #title
                    self.recordingTitle = True
                elif attr[0] == 'class' and attr[1] == 'year':
                    #year
                    self.recordingYear = True
                elif attr[0] == 'class' and attr[1] == 'scanstatus':
                    #scan status
                    self.recordingScanStatus = True
        if tag == 'img':
            for attr in attrs:
                if attr[0] == 'src' and attr[1].startswith('https://manga.madokami.al/images'):
                    jsonData[current_path]["manga_image"] = base64.b64encode(s.get(attr[1]).content).decode()


    def handle_endtag(self, tag):
        if tag == 'table':
            self.insideIndexTable = False
        if tag == 'tbody':
            self.insideTbody = False
        if tag == 'a':
            if self.recordingGenre:
                self.recordingGenre = False
            if self.recordingTag:
                self.recordingTag = False
            if self.recordingAuthor:
                self.recordingAuthor = False
        if tag == 'span':
            if self.recordingYear:
                self.recordingYear = False
            if self.recordingTitle:
                self.recordingTitle = False
            if self.recordingScanStatus:
                self.recordingScanStatus = False

    def handle_data(self, data):
        if self.recordingGenre:
            jsonData[current_path]["genres"].append(data)
        if self.recordingTag:
            jsonData[current_path]["tags"].append(data)
        if self.recordingAuthor:
            jsonData[current_path]["authors"].append(data)
        if self.recordingYear:
            jsonData[current_path]["year"] = data
        if self.recordingTitle:
            jsonData[current_path]["title"] = data
        if self.recordingScanStatus:
            jsonData[current_path]["scanStatus"] = data

parser = MyHTMLParser()
parser.feed(content.decode())
logger.info(links)
allLinks = []
allLinks.extend(links)
links.clear()
allLinks.remove('/Requests')
allLinks.remove('/Admin%20cleanup')

logger.info(len(allLinks))
while(len(allLinks)):
    link = allLinks.pop()
    location = mangaDir + urllib.parse.unquote(link)
    current_path = location
    if os.path.isdir(location) or not os.path.isfile(location):
        jsonData[current_path] = {
            "title": "",
            "year": "",
            "genres": [],
            "tags": [],
            "authors": [],
            "relatedSeries": [],
            "scanStatus": "",
            "mangaUpdatesLink": "",
            "manga_image": ""
        }

        logger.info("CRAWLING: " + location)
        r = s.get(url + link)
        content = r.content
        try:
            parser.feed(content.decode())
        except Exception:
            logger.info(f'  Len: {sys.getsizeof(content)}  DOWNLOADING: ' + urllib.parse.unquote(link))
            try:
                os.makedirs(os.path.dirname(location))
            except FileExistsError:
                pass
            with open(location, 'wb') as newFile:
                newFile.write(content)
                newFile.close()
            totalSize += sys.getsizeof(content)
        time.sleep(0.1)
        allLinks.extend(links)
        links.clear()
f = open("madokami_data.json", "w")
f.write(json.dumps(jsonData))
f.close()
print(f"Total size downloaded: {totalSize} bytes")

