#!/usr/bin/python

import logging
from TwitterScraper import TwitterScraper

logging.basicConfig(filename='example.log',level=logging.DEBUG)
scraper = TwitterScraper(("politie","ramp"),4.9,52.5,5)
scraper.loop()
