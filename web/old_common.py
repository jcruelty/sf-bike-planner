#!/usr/bin/python

"""
common.py

Copyright 2009 Amar Pai

If this code is used you must credit me and keep it under a BSD open source
license (freely redistributable/modifiable under these same terms)

This script holds common functions used by different bikemap scripts.
In particular it has functions for configuration, setting up logging, etc.
"""

import cgi,cgitb
import cPickle
from datetime import datetime
import logging
from logging import debug, info, warning, error
import math
import os
from os.path import join, exists, splitext
import sys
import time
import urllib
from xml.dom.minidom import parse, parseString

cgitb.enable(format='txt')

RUNNING_LOCALLY=True

# constants (filepaths)
SVNROOT = os.environ.get('SFBIKE_SVNROOT', os.path.abspath(os.getcwd() + "/.."))
RAW = SVNROOT + "/data/raw"
IMPORTED = SVNROOT + "/data/imported"
OUTPUT = SVNROOT + "/data/output"
MAPREDUCE_INPUT = SVNROOT + "/data/mapreduce-input"
LOGDIR = SVNROOT + "/src/logs"
HTDOCS = SVNROOT + "/htdocs"
DATASETS = ["TIGER Road Data (2007)",
						"MTC Bike Data (2008)", 
						"SFGOV (nad83)", 
						"SFGOV (wgs84)",
						"SFGOV (physical contours)"]
GISDIRS =["%s/%s" % (RAW, dataSet) for dataSet in DATASETS]

CONTOUR_SHPFILE = RAW + "/SFGOV_wgs84/phys_contours_wgs.shp"
CONTOUR_DBFFILE = RAW + "/SFGOV_wgs84/phys_contours_wgs.dbf"
ELEVATION_XY = IMPORTED + "/elevation_xy.pkl"
ELEVATION_YX = IMPORTED + "/elevation_yx.pkl"
RAW_ELEVATIONS = IMPORTED + "/elevation_tuples.pkl"
ELEVATIONS= IMPORTED + "/sorted_elevation_tuples.pkl"
GRAPH = HTDOCS + '/Graph.pkl'
PTS_XY = HTDOCS + '/ptsXY.pkl'
PTS_YX = HTDOCS + '/ptsYX.pkl'
PT2INTERSECT = OUTPUT + '/pt2intersect.pkl'
LOOKUP_ERROR_PTS = OUTPUT + '/lookupErrorPts.pkl'
COMPUTED_ELEVATIONS = OUTPUT + '/computedElevations.pkl'
MAPREDUCE_COMPUTED_ELEVATIONS = OUTPUT + '/mapreduceComputedElevations.pkl'
LOOKED_UP_ELEVATIONS = OUTPUT + '/lookedUpElevations.pkl'
SAMPLED_ELEVATIONS = ELEVATIONS + '-sampled-1-in-10000'
FIXED_SLOPE_GRAPH = OUTPUT + '/FixedSlopeGraph.pkl'
OLD_GRAPH_WITH_HIGHWAYS = HTDOCS + '/OldGraphWithHighways.pkl'
NO_HIGHWAY_GRAPH = HTDOCS + '/NoHighwayGraph.pkl'

# indices into edge debug (e.g. ('bike lane', 'SMITH ST', .34322))
TYPE=0
NAME=1
SLOPE=2

YAHOO_APP_ID='7IxCKuHV34FWuK92O2UxG1t0ycuHLXh4zXN7oe0j4tyIpnhH.WcaKTjEuwmnLC4-'

def timed(f):
  def _inner(*args, **kwargs):
    start=time.time()
    result = f(*args,**kwargs)
    debug('%s elapsed time: %s s' % (str(f),time.time()-start))
    return result
  return _inner

def fetchUrl(url):
  debug('Requesting %s' % url)
  f = urllib.urlopen(url)
  response = f.read()
  debug('Response:\n%s' % response)
  return response

def getText(element):
  return element.firstChild.nodeValue

def geocode(address):
  """
  returns {'lat':123.45,'lon':37.111} or None
  """
  url = 'http://api.local.yahoo.com/MapsService/V1/geocode?'
  url += urllib.urlencode({'appid':YAHOO_APP_ID, 'location':address})
  response = fetchUrl(url)
  dom = parseString(response)
  try:
    latitudes = dom.getElementsByTagName('Latitude')
    longitudes = dom.getElementsByTagName('Longitude')
    lat=float(getText(latitudes[0]))
    lon=float(getText(longitudes[0]))
    #print 'Lats: %s Longs: %s' % (latitudes,longitudes)
    return {'lat':lat,'lon':lon}
  except Exception, e:
    return None

def strPtToFloatPt(strPt):
  if type(strPt) != str or strPt.find(',')<0:
    raise Exception('cannot convert %s (%s) from strPt to floatPt' % (strPt,type(strPt)))
  x, y = strPt.split(',')
  return (float(x),float(y))

def floatPtToStrPt(floatPt):
  if type(floatPt) != tuple or type(floatPt[0])!=float or type(floatPt[1]) != float:
    raise Exception('cannot convert %s (%s) from floatPt to strPt' % (floatPt,type(floatPt)))
  strPt = '%.5f,%.5f' % (floatPt[0],floatPt[1])
  return strPt

def convertToLatLon(ft_dist):
  """
  convert distance in ft to lat lon dist
  """
  return ft_dist * (.000003)

def convertToFeet(latlong_dist):
  """
  coords are in lat/long
  conversion from distances in those units to ft is:
  0.000003 units of ours = 1 ft
  so to convert our distance to ft, multiply our distance by 1/0.000003
  """
  return latlong_dist * (1.0/0.000003)

def getDistance(pt1, pt2):
  """
  get_distance(pt1, pt2)

  takes two pts, where pt is tuple of two floats, i.e. (x,y)
  returns euclidean distance between those pts
  """
  if type(pt1)==str:
    pt1=strPtToFloatPt(pt1)
  if type(pt2)==str:
    pt2=strPtToFloatPt(pt2)
  x1, x2 = pt1[0], pt2[0]
  y1, y2 = pt1[1], pt2[1]
  return math.sqrt(math.pow(abs(x1 - x2), 2) + math.pow(abs(y1 - y2), 2))

def getDistanceInFeet(pt1, pt2):
  return convertToFeet(getDistance(pt1, pt2))

# return a string (with ft or miles at end)
def humanReadableFt(ft):
    miles = ft / 5280.0
    if miles >= 0.1:
        return "%.1f miles" % miles
    else:
        return "%d feet" % int(ft)

def getAllUniquePts(graph):
  dPts={}
  for pt1 in graph:
    dPts[pt1]=1
    for pt2 in graph[pt1]:
      dPts[pt2]=1
  pts=dPts.keys()
  pts.sort()
  return pts 

# returns (closestOtherPt,distance)
@timed
def findClosestPoint(ourPt,otherPts,searchRadius=500.0):
  if type(ourPt) == str:
    ourPt=strPtToFloatPt(ourPt)
  ourLon,ourLat=ourPt
  if searchRadius:
    searchRadius = convertToLatLon(searchRadius) # only search pts from lon-500ft to lon+500ft
    minPt=(ourLon-searchRadius,ourLat)
    maxPt=(ourLon+searchRadius,ourLat)
    i=bisect_left(otherPts,minPt)
    j=bisect_right(otherPts,maxPt)
  else:
    i=0
    j=len(otherPts)
  closestPt=minDistance=None
  for pt in otherPts[i:j]:
    otherPt = ((type(pt)==str) and strPtToFloatPt(pt)) or pt
    distance = getDistance(ourPt, otherPt)
    if not minDistance or (distance < minDistance):
      minDistance = distance
      closestPt = pt
  assert closestPt != None
  return closestPt

def importedFilename(name):
	return IMPORTED + '/' + name
	
def outputFilename(name):
  return OUTPUT + '/' + name

def saveToOutput(datastruct, name):
  save(datastruct, outputFilename(name))

def saveToImported(datastruct, name):
  save(datastruct, importedFilename(name))

def logFilename(name):
  d=datetime.now()
  timestamp=d.strftime('%I').strip('0')+d.strftime(':%M%p-').lower()+d.strftime('%a-%B%d')
  return LOGDIR + '/%s-%s' % (name,timestamp)

def setupLogging(logName=None,logLevel=logging.DEBUG):
  """
  Set up logging (format, level, etc) based on inputs,
  environmental variables and constants.
  """
  global curLogName
  if 'curLogName' in globals() and (not logName or curLogName==logName):
    warning('setupLogging(%s) has already been called-- ignoring' % logName)
    return

  curLogName = logName or 'bikemap'

  # set up logging handlers - verbose output to file, terse to stdout
  streamHandler = logging.StreamHandler(sys.stdout)
  streamHandler.setLevel(logLevel)
  streamHandler.setFormatter(logging.Formatter('%(message)s\n'))

  logFile = logFilename(logName)
  fileHandler = logging.FileHandler(logFile, 'w')
  fileHandler.setLevel(logLevel)
  fileHandler.setFormatter(logging.Formatter('%(asctime)s (line %(lineno)d):\n%(message)s\n', '%I:%M:%S'))

  rootLogger = logging.getLogger()
  rootLogger.setLevel(logLevel)
  rootLogger.handlers = [streamHandler, fileHandler]

  startupMsg = '\n===================== START LOG REAL ====================\n'
  startupMsg += 'Start time: %s\n\n' % time.strftime("%a, %d %b %Y %I:%M:%S %p", time.gmtime())
  startupMsg += 'SVNROOT = %s\nLOGFILE = %s' % (SVNROOT, logFile)

  logging.critical(startupMsg)

def save(data, outputPath):
  """
  pickles struct to sOutputPath using protocol 2
  """
  f = open(outputPath, 'wb')
  try:
    cPickle.dump(data, f, cPickle.HIGHEST_PROTOCOL)
  finally:
    f.close()
  debug('Saved ' + outputPath)

def load(path):
  """
  returns unpickled struct loaded from sPath
  """
  start=time.time()
  debug('Loading ' + path)
  f = open(path, 'rb')
  try:
    data = cPickle.load(f)
    extra = ''
    if type(data) in [list,tuple,dict]:
      extra = 'len=%d, ' % len(data)
    debug('Done. Loaded %s,%sin %f secs.' % (type(data),extra,time.time()-start))
  finally:
      f.close()
  return data

def dumpvar(x, msg=""):
  s = "%s:\tvalue=%s type=%s " % (msg, x, type(x))
  if type(x) == list and len(x) < 10:
    s += " length=%d, first=%s, first_types=%s" % (len(x), x[0], ",".join([str(type(y)) for y in x[0]]))
  return s

def printvar(x, msg=""):
  print dumpvar(x, msg)

def resample(filename, sampleRate=100):
  """
  reduce datastruct by taking every nth (e.g. 100th) item
  save as filename_sampled_n
  """
  debug('Resampling %s at rate %d' % (filename,sampleRate))
  data=load(filename)
  if type(data) == dict:
    newData = {}
    keys = data.keys()
    for i in range(0, len(keys), sampleRate):
      newData[keys[i]]=data[keys[i]]
  elif type(data) == list or type(data) == tuple:
    newData = []
    for i in range(0, len(data), sampleRate):
      newData.append(data[i])
  else:
    raise Exception('can only resample lists, tuple and dict-- not %s' % type(data))

  newFilename = filename + '-sampled-1-in-%d' % sampleRate
  save(newData, newFilename)
  debug('Resampled as %s - len %d' % (newFilename, len(newData)))
  return newData

# main #
if __name__ == "__main__":
  if RUNNING_LOCALLY:
    setupLogging()
  else:
    print "Content-Type: text/plain\n"  
    print 'Cache-Control: no-store, no-cache,  must-revalidate\n\n'
    print 'Everything ok!'
