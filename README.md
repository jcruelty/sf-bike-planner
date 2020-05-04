# SF bike route planner - FAQ / implementation details

https://docs.google.com/document/d/1wRed3SGmGWAApFAfh9gEkwoVoK5p7T5LsTEg_qLgq-8/edit

Last revised 2007

===============================
1. Creation of needed data sets
===============================

SFGov has GIS data sets publically available at:

http://gispub02.sfgov.org/website/sfshare/index.htm

You have to sign up.  Once you do you can download datasets.  I used the following sets:

http://gispub02.sfgov.org/website/sfshare/catalog/dpt_bike_network.zip
http://gispub02.sfgov.org/website/sfshare/catalog/phys_contours_wgs.zip
http://gispub02.sfgov.org/website/sfshare/catalog/stclines_streets.zip
http://gispub02.sfgov.org/website/sfshare/catalog/stintersections.zip

The coordinates are in a local coordinate system - Lambert Conformal Conic, datum NAD83.  To avoid having to geocode all points, I needed to get these data sets in WGS 84 format.  This format is "global latitude longitude" & it's what Yahoo and Google maps use.  I experimented with trying to do the conversion myself using the tool:

http://proj.maptools.org/man_cs2cs.html

But I couldn't figure out the right parameters to use.  Luckily, Jeff Johnson (senior GIS apps developer for the city, Jeffrey.Johnson@sfgov.org) was kind enough to provide me the data in WGs84 format.  He converted it using a GIS app.  If further conversions are needed, Jeff suggested using www.safe.com's FME product (evaluation copy can be used for 2 weeks)
Jeff also provided me with an additional data set containing 1-way street data (e.g. which streets are 1-way in a certain direction).  Though out of date, it was better than nothing.  This data is not publically availalbe at the moment.

For understanding coordinate systems, Charlie Savage's notes are useful

On Coordinate Systems - http://cfis.savagexi.com/articles/2006/04/20/on-coordinate-systems
Geocentric Coordinate Systems - http://cfis.savagexi.com/articles/2006/04/23/geocentric-coordinate-systems
Projections - http://cfis.savagexi.com/articles/2006/04/30/projections
Coordinate Systems - Putting Everything Together - http://cfis.savagexi.com/articles/2006/05/02/coordinate-
Google Maps Deconstructed - http://cfis.savagexi.com/articles/2006/05/03/google-maps-deconstructed

To view the GIS data sets, I used the free ArcGIS tool available at the url below.  The querying methods were particularly useful when evaluating data.

http://www.esri.com/software/arcexplorer/about/arcexplorer-education.html

Once I had the GIS data sets, I needed to convert them into data sources I could use.  There are several different 'views' on the data that are needed.  The primary one is a weighted directed graph where edges are connections between intersection points.  Another is a listing of network points sorted by their WGS84 coordinates.

The GIS data sets are in "shapefile" format.  To read this format I used the "pyshapelib" Python bindings for the very useful C library shapelib.

http://shapelib.maptools.org/
ftp://intevation.de/users/bh/pyshapelib/

Also very useful is this utility, which converts a shapefile to XLS format (from which one can export a comma delimited text file):

http://www.obviously.com/gis/shp2text/

Most of the data could be read in directly using pyshapelib, but the contour data set is too large for that to be efficient.  So a preprocessing step was to convert the contours data to XLS format, then 'prune' it by eliminating 2/3 of the rows.  I reasoned that since the data points were so close together, we could just map network points to their nearest contour point if no exact match was found. 
 
Once preprocessing was done, I wrote Python scripts to create the 'views' mentioned above.  I represented the graph as a dict of dicts and pickled the datasets using python's cPickle marshalling library.  The conversion scripts ran as follows:

1) read in stclines_streets to build edge graph
2) read in dpt_bike_network to add bike edges
3) read in stintersections to build list of points by coordinates
4) add inclines to edge graph

Some massaging of the data was required; e.g. inconsistent st names, 03rd st vs 3rd st.  Also a lot of bike edges are unnamed.  Also there was no one way data, as mentioned earlier, and the data that Jeff sent me is old.  Also, I had to decide what precision to use for the floating point coordinates; too many units of precision and edges that should 'meet' don't due to tiny differences in the GIS coordinates.  Not enough and edges that shouldn't meet will be shown as meeting.  I went with 3 decimal places. 

TODO: need a better way to modify the pickled data; maybe use a mysql db that has ability to 'export' as pkl file?

=========================
2. Finding weighted path
=========================

Once I had the data sets, path planning boiled down to the well known single shortest path problem.  I use Dijkstra's algorithm.  To calculate the 'weight' of an edge, I use the formula:

weight = euclidean distance(v1, v2) * typemultiplier * (incline > maxallowed ? LARGE_INT : 1)

Type multiplier is the user-set multiplier for each type of edge (bike lane, bike path, road, etc.)  Through changing the multipliers, a path can be made 'shortest', 'most bike friendly', etc.

TODO: tweak the multipliers; add multiplier for 'straight path' (favor straight paths over ones with lots of turns by checking if street name of P[P[v1]] = street name of P[v1]; if not, a turn occurred so use straight path multiplier; add multiplier for speed limit (if data exists)

TODO: use A* search to speed things up

===============================
3. Calculating start/end points
===============================

Given start/end points in WGS 84, we find the closest points in our graph.  To avoid having to look at every point in the graph, I kept track of the current 'closest' distance and ignored any points where (inputPt.x - checkedPt.x)^2 > current closest, or (inputPt.y - checkedPt.y)^2 > current closest. 

Note: after experimenting, I found that for the relatively small number of points used in this app, it's faster to just brute-force compare input point to every point in the graph.

Once the start/end points are determined, Dijkstra can be run.  Once it concludes, we can chain backwards from the end point, appending each point's predecessor to the path until we hit the start point.  Then we build the path output by looking up street name of each edge in the path, along with distance covered by that edge and max incline of that edge.  This finally gets stuffed using json and returned.

=======================================
4. AJAX, geocoding, rendering (client stuff)
=======================================

The input page is a simple form, but it has a Yahoo maps widget embedded in it.  We use the Yahoo maps API to geocode the start/end addresses.  Geocoding and all calls to server-side python scripts are done using XMLHTTPRequest.

Yahoo MAPS 3.4 API docs - http://developer.yahoo.com/maps/ajax/index.html
Geocoding example - http://api.maps.yahoo.com/ajax/examples/v3.4/geocode.html
Introduction to Ajax - http://www.xml.com/pub/a/2005/02/09/xml-http-request.html

The find_path python script runs as a cgi script on the server.  As mentioned above, it returns the output path, along with html directions and some other data, in Javascript object notation.  I chose JSON over XML because XML is really verbose and there's not much likelihood of my Python scripts getting called by other clients (so portability is less of a concern than conciseness and ease of use.)

TODO: is my Ajax code that solid?  Does it work on all browsers?  where are all the other AJAX doc sites I used?  How about JSON doc sites?

Once we get back the path, rendering it is straightforward using the maps API.

=============================================
5. Misc notes
=============================================
I couldn't use any newer features of Python because my webserver is only running 2.1.xx [todo verify]
If the code were ported to a platform that supports Python 2.5 it could be made cleaner.

TODO: profiling, logging, more robust handling of error input, slider for incline, fix data bugs & paths with no names.  (Highway 280 is not bike friendly!!!)

Python scripts running on server must be chmod 0777'd
CGI debugging done through server
Packing format for pkl files is binary; tried using DBMs but couldn't get DBM files created in Win32 to work in Python

XMLHTTPRequest does not work cross-site; thus we can't do geocoding queries except using the embedded Yahoo object.  If there were a proxy on the server hosting my python files, that could be used to do geocoding requests via HTTP.

It would be nice to have a better interface for getting user feedback.
Also to test on more platforms.

Copyright 2007 Amar Pai


