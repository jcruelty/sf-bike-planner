#!/usr/bin/python

from common import *
from bisect import bisect_left, bisect_right

def getAllUniquePts(graph):
  dPts={}
  for pt1 in graph:
    dPts[pt1]=1
    for pt2 in graph[pt1]:
      dPts[pt2]=1
  pts=dPts.keys()
  pts.sort()
  return pts 

# returns (pt, elevation)
@timed
def findClosestPoint(ourPt,elevations,searchRadius=500.0):
  if type(ourPt) == str:
    ourPt=strPtToFloatPt(ourPt)
  ourLon,ourLat=ourPt
  if searchRadius:
    searchRadius = convertToLatLon(searchRadius) # only search pts from lon-500ft to lon+500ft
    minPt=(ourLon-searchRadius,ourLat)
    maxPt=(ourLon+searchRadius,ourLat)
    i=bisect_left(elevations,minPt)
    j=bisect_right(elevations,maxPt)
  else:
    i=0
    j=len(elevations)
  closestTup=minDistance=None
  for tup in elevations[i:j]:
    otherPt = (tup[0], tup[1])
    distance = getDistance(ourPt, otherPt)
    if not minDistance or (distance < minDistance):
      minDistance = distance
      closestTup = tup  
  msg = 'Finding closest to %s in range %d to %d (%d items)\n' % (str(ourPt),i,j,j-i)
  msg += '\nDone. Closest=%s, distance=%d ft' % (str(closestTup),convertToFeet(minDistance))
  info(msg)
  assert closestTup != None
  return ((closestTup[0],closestTup[1]),closestTup[2])

@timed
def getElevations(graphFile=GRAPH,outputFile=COMPUTED_ELEVATIONS,elevationFile=ELEVATIONS):
  info('Getting elevations for all points in %s' % graphFile)
  G = load(graphFile)
  allPoints = getAllUniquePts(G)
  nPoints = len(allPoints)
  elevations=load(elevationFile)
  elevations.sort()
  if os.path.exists(outputFile):
    output = load(outputFile)
    startIndex=output.get('indexOfLastCompleted',-1)+1
    info('Loaded previous %s; continuing at index %d' % (outputFile,startIndex))
  else:
    output={}
    startIndex=0

  for i in range(startIndex, nPoints):
    curPtStr = allPoints[i]
    curPtFloat = strPtToFloatPt(curPtStr)
    closestPt,elevation=findClosestPoint(curPtFloat, elevations)
    output[curPtStr]=elevation
    output['indexOfLastCompleted']=i
    save(output,outputFile)
    info('completed %d of %d' % (i, nPoints))
  info('done')

"""
Updates main graph with new slope values, using latest
elevation data from web lookup and/or nearest-pt computations
on contour map.  Outputs new graph to specified filename.

TODO: use mapreduce to compute nearest contour-map pt for
all pts in G.  Also use untrucated floats for lat/long,
rather than truncated versions from G.
"""
@timed
def fixSlopes(inputFile=GRAPH,outputFile=FIXED_SLOPE_GRAPH):
  oldGraph=load(inputFile)
  info('fixSlopes: inputfile=%s\n%s' % (inputFile,getGraphStats(oldGraph)))

  elevations=load(COMPUTED_ELEVATIONS)
  newGraph=oldGraph.copy()
  for strPt1 in oldGraph:
    for strPt2 in oldGraph[strPt1]:
      type,name,oldIncline = oldGraph[strPt1][strPt2]
      floatPt1= strPtToFloatPt(strPt1)
      floatPt2= strPtToFloatPt(strPt2)
      run = getDistanceInFeet(floatPt1, floatPt2)
      rise  = elevations[strPt2] - elevations[strPt1]
      newIncline = rise/run
      if newIncline != oldIncline:
        info("G[%s][%s]: Old incline: %f\nNew incline: %f" % (strPt1, strPt2, oldIncline, newIncline))
        newGraph[strPt1][strPt2] = (type,name,newIncline)
  save(newGraph, outputFile)

  info('Done. Processed %d edges.\noutputfile: %s\n%s' % (len(oldGraph), outputFile,getGraphStats(newGraph)))

def getGraphStats(G):
  leastSteepEdge=steepestEdge=('road','UNKNOWN',0.0)
  sumSlopes=numSlopes=0.0

  for v1 in G:
    for v2 in G[v1]:
      edge=G[v1][v2]
      slope=edge[2]
      if slope < leastSteepEdge[2]:
        leastSteepEdge=edge
      if slope > steepestEdge[2]:
        steepestEdge=edge
      numSlopes += 1
      sumSlopes += slope

  avgSlope=sumSlopes/numSlopes

  return '\n'.join(('Avg. slope: %f' % avgSlope,
    'Steepest edge: %s' % str(steepestEdge),
    'Least steep edge: %s' % str(leastSteepEdge)))

if __name__ == "__main__":
  setupLogging(logName="fix_elevations",logLevel=logging.INFO)
  #getElevations()
  #fixSlopes()
  oldGraph=load(GRAPH)
  newGraph=load(FIXED_SLOPE_GRAPH)
  info('Old graph:\n%s\n----\nNew graph:\n%s\n--------\n' % (getGraphStats(oldGraph),getGraphStats(newGraph)))
 
