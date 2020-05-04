#!/usr/bin/python
from common import *

"""
API documentation:
http://www.earthtools.org/webservices.htm#height

To access the service:
http://www.earthtools.org/height/<latitude>/<longitude>

Returns the following XML:
<?xml version="1.0" encoding="ISO-8859-1" ?>
<height xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://www.earthtools.org/height.xsd">
    <version>1.0</version>
    <location>
        <latitude>52.4822</latitude>
        <longitude>-1.8946</longitude>
    </location>
    <meters>141</meters>
    <feet>462.6</feet>
</height>

Feet may be Unknown or -9999
"""

def lookupElevation(coords):
  if not coords:
    return None

  lat, lon = coords['lat'], coords['lon']
  url = 'http://www.earthtools.org/height/%f/%f' % (lat,lon)
  time.sleep(1) # make sure we don't violate ToS
  response = fetchUrl(url)
  dom = parseString(response)
  feet = getText(dom.getElementsByTagName('feet')[0])
  #print 'Elevation (ft): %s' % feet
  if feet != 'Unknown' and feet != "-9999":
    elevation = float(feet)
    #print 'Elevation (float): %f' % elevation
  else:
    elevation = None
  return elevation

def lookupAgain(retryPts, outputfile=LOOKED_UP_ELEVATIONS):
  """ look up pts and write results if any to existing file """
  info("lookupAgain")
  lookedUpPts = load(outputfile)

  # sanity checking 
  for pt in retryPts:
    if pt in lookedUpPts:
      raise Exception('%s exists both retryPts and lookedUpPts' % str(pt))
  typea=type(retryPts[0])
  typeb=type(lookedUpPts.keys()[0])
  if typea != typeb:
    raise Exception('incompatible key types in retryPts/lookupPts: %s/%s' % typa,typeb)
  
  success = 0
  for pt in retryPts:
    if type(pt)==tuple:
      long,lat = pt
    else:
      long,lat = strPtToFloatPt(pt)
    elevation = lookupElevation({'lat':lat,'lon':long})
    if elevation:
      info('Retry succeeded for %s' % str(pt))
      success += 1
      lookedUpPts[pt] = elevation
      save(lookedUpPts,outputfile)
    else:
      info('Retry failed for %s' % pt)
  info('Done - %d of %d retried successfully' % (success,len(retryPts)))

def lookupAll(inputfile=GRAPH, outputfile=LOOKED_UP_ELEVATIONS,
              errorfile=LOOKUP_ERROR_PTS):
  """
  Lookup elevations of all pts in inputfile
  Outputs:
    lookedUpGraphPts: <dict> key=strPt,value=elevation
                      points that were looked up successfully
    lookupErrorPts: <list> strPt
                    points where lookup failed

  Note: graph uses (.5f,.5f) for pts.  We purposely round to
  less precision so intersections occur.  But, using rounded
  values here means we don't get the most accurate elevations
  possible, since our coords are not exact.

  TODO: lookup elevations at earlier stage when full precision
  pts still exist, and pass along elevation values to graph
  rather than looking them up afterwards.
  """
  # Every terminal pt is a starting pt but not vice versa.
  # So G.keys() gives us all points in G.
  inputPts = load(inputfile)
  lookedUpPts = {}
  errorPts = []
  interval = len(inputPts)/1000
  for pt in inputPts:
    long,lat = strPtToFloatPt(pt)
    elevation = lookupElevation({'lat':lat,'lon':long})
    if elevation:
      lookedUpPts[pt]=elevation
    else:
      errorPts.append(pt)
      info('failed to lookup elevation for %s' % pt)
    if len(lookedUpPts) % interval == 0:
      info('processed: %d; error: %d' % (len(lookedUpPts),len(errorPts)))
      save(lookedUpPts, outputfile)
      if len(errorPts) > 0:
        save(errorPts,errorfile)

def retryMissingGraphPoints():
  lookedUp=load(LOOKED_UP_ELEVATIONS)# elevations looked up via web
  computed=load(COMPUTED_ELEVATIONS) # elevations computed via contour map
  G=load(GRAPH)
  missing=[]
  for pt in G:
    if (pt not in lookedUp) and (pt not in computed) and (pt not in missing):
      missing.append(pt)
  info('retryMissingGraphPoints- missing %d of %d' % (len(missing),len(G)))
  lookupAgain(missing, LOOKED_UP_ELEVATIONS)

if __name__ == '__main__':
  #testElevation=lookupElevation(geocode('20th and missouri, sf, ca'))
  #lookup_all()
  #retryErrorPts()fix_elevations-11:45pm-Wed-June24
  setupLogging('lookup_elevations',logging.INFO)
  retryMissingGraphPoints()
  
