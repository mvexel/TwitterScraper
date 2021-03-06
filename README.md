TwitterScraper
==============

Scrapes twitter with regular intervals for geotweets containing one or more search terms. It uses the Twitter Search API exclusively, so you don't need to worry about hitting any usage limits.

Requirements
------------

This module uses [Shapely]("http://gispython.org/shapely/docs/1.2/index.html"), [psycopg2]("http://initd.org/psycopg/") and [geopy]("http://code.google.com/p/geopy/") so install those using pip or easy_install. 

You need a PostGIS database with a table to hold the tweets (see below for the schema).

Usage
-----

A sample (samplescraper.py) is included to show how the scraper is invoked:

	scraper = TwitterScraper(("politie","ramp"),4.9,52.5,5)
	scraper.loop()

This initializes a scraper object with the search terms "politie" and "ramp", looking for geotweets approximately 5km around (4.9,52.5).

The constructor takes the following arguments:	

* terms -- A tuple containing the search terms. The search performed is for any, not all of these terms
* lon -- Longitude (x) of the coordinate to search around. 
* lat = Latitude (y) of the coordinate to search around.  
* radius = radius in km of the coordinate to search around. 
* interval = Optional. Interval in seconds between searches. Defaults to 60 (1 minute) 
* language = Optional. Language of tweets to search for. [ISO 639-1]("http://en.wikipedia.org/wiki/ISO_639-1")-code. Defaults to Dutch (nl)

When you re-initialize a scraper and start scraping again, it will pick up where it left off - it will always take the newest tweet already in the DB as a starting point for the search.

Wish list
---------
* The max number of results returned per response is 100. Situations with more than 100 results are not handled yet. 
* Make it work as a daemon
* Wrap it in a proper command line tool, taking arguments
** To empty current DB
** To set the scraper arguments (see above)

DB schema
---------

You will need a PostGIS database containing a table like this:

	CREATE TABLE tweets
	(
	  "text" character varying,
	  userid bigint,
	  loc geometry,
	  id bigint NOT NULL,
	  datetime timestamp with time zone,
	  CONSTRAINT pkey_id PRIMARY KEY (id),
	  CONSTRAINT enforce_dims_loc CHECK (st_ndims(loc) = 2),
	  CONSTRAINT enforce_geotype_loc CHECK (geometrytype(loc) = 'POINT'::text OR loc IS NULL),
	  CONSTRAINT enforce_srid_loc CHECK (st_srid(loc) = 4326)
	)
	WITH (
	  OIDS=FALSE
	);
