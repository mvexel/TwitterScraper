import httplib
import json
import logging
import socket
import time
import urllib
import re
from shapely.wkt import dumps, loads
from shapely.geometry import asPoint
import psycopg2
import psycopg2.extensions
from psycopg2.extensions import adapt, register_adapter, AsIs
from datetime import datetime,timedelta
from geopy import geocoders

SEARCH_HOST="search.twitter.com"
SEARCH_PATH="/search.json"
PG_DBNAME = "disaster"
PG_USER = "disaster"
PG_PASS = "disaster"

class Point(object):
	def __init__(self,x,y):
		self.x = x
		self.y = y
	def __init__(self,xy):
		self.x = xy[0]
		self.y = xy[1]

def adapt_point_wkt(point):
	return AsIs("ST_GeomFromText(%s,4326)" % (adapt(asPoint([point.x,point.y]).wkt)))	
	
register_adapter(Point, adapt_point_wkt)


class TwitterScraper(object):
	def __init__(self, terms, lon = None, lat = None, radius = None, interval = 60, language = "nl"):
		conn = psycopg2.connect("dbname="+PG_DBNAME+" user="+PG_USER+" password="+PG_PASS)
		cur = conn.cursor()
		cur.execute("SELECT max(id) from tweets")
		max = cur.fetchone()
		if max[0] is None:
			logging.debug("max was none")
			self.max_id=0
		else:
			logging.debug(max[0])
			self.max_id = int(max[0])
		cur.close()
		conn.close()
		self.terms = terms
		self.interval = interval
		self.lon = lon
		self.lat = lat
		self.radius = radius
		self.language = language
		self.terms = terms
		
	def search(self):
		params = {}
		c = httplib.HTTPConnection(SEARCH_HOST)
		logging.debug(' '.join(self.terms))
		params['ors'] = ' '.join(self.terms)
		params['rpp'] = 100
		if self.max_id is not None:
			params['since_id'] = self.max_id
			if self.lat and self.lon and self.radius:
				params['geocode'] = ",".join((str(self.lat),str(self.lon),"{0}km".format(self.radius))) 
		path = "%s?%s" %(SEARCH_PATH, urllib.urlencode(params))
		logging.debug("".join((SEARCH_HOST,path)))
		try:
			c.request('GET', path)
			r = c.getresponse()
			data = r.read()
			c.close()
			try:
				result = json.loads(data)
			except ValueError:
				return None
			if 'results' not in result:
				return None
			self.max_id = result['max_id']
			return result['results']
		except (httplib.HTTPException, socket.error, socket.timeout), e:
			logging.error("search() error: %s" %(e))
			return None

	def loop(self):
		while True:
			logging.info("Start zoeken naar %s" % ', '.join(self.terms))
			data = self.search()
			if data:
				logging.info("%d nieuwe vondst(en)" %(len(data)))
				self.submit(data)
			else:
				logging.info("Geen nieuwe vondsten")
			logging.info("Klaar. %d Seconden wachten..."
					%(self.interval))
			time.sleep(float(self.interval))

	def submit(self, data):
		logging.debug("submitting %d tweets" % len(data))
		conn = psycopg2.connect("dbname="+PG_DBNAME+" user="+PG_USER+" password="+PG_PASS)
		cur = conn.cursor()
		llregex = re.compile('\d+\.\d+')
		for tweet in data:
			logging.debug("parsing tweet...")
			offset=0
			lonlat = []
			for m in llregex.finditer(tweet["location"]):
				lonlat.insert(0,float(m.group()))
			if len(lonlat)<2:
				logging.info("got inexact location: %s - geocoding..." , tweet["location"])
				try:
					g = geocoders.Google()
					place, (lat, lng) = g.geocode(tweet["location"])
					logging.info("geocoded %s as %s, coords %f,%f" % (tweet["location"],place,lng,lat))
					lonlat = [lng,lat]
				except:
					logging.warn("geocoding failed, skipping this tweet...")
					continue
			p = Point(lonlat)
			timestring = str(tweet["created_at"])
			try:
				offset = int(timestring[-5:])
			except:
				logging.debug("Could not parse timezone from %s" % timestring)
			delta = timedelta(hours = offset / 100)
			dt = datetime.strptime(tweet["created_at"][:-6], "%a, %d %b %Y %H:%M:%S")
			dt -= delta
			logging.debug("time from string %s is %s" % (timestring,dt))
			logging.debug(asPoint(lonlat).wkt)
			logging.debug(tweet["text"])
			logging.debug(cur.mogrify("INSERT INTO tweets (id,loc,userid,text,datetime) VALUES (%s, %s, %s, %s, %s)", (int(tweet["id_str"]),p,int(tweet["from_user_id"]),tweet["text"], dt)))
			try:
				cur.execute("INSERT INTO tweets (id,loc,userid,text,datetime) VALUES (%s, %s, %s, %s, %s)", (int(tweet["id_str"]),p,int(tweet["from_user_id"]),tweet["text"], dt))
			except:
				logging.error("insertion failed")
		conn.commit()
		cur.close()
		conn.close()
