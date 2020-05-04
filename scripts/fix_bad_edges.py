#!/usr/bin/python

from common import *
try:
  from collections.defaultdict import defaultdict
except:
  try:
    from util.defaultdict import defaultdict
  except:
    print 'Warning, could not import default dict'

setupLogging('fix_bad_edges')

def get280Edges(inputFile=NEW_GRAPH):
  G=load(inputFile)
  matches=defaultdict(dict)
  for v1 in G:
    for v2 in G[v1]:
      edgeInfo=G[v1][v2]
      roadName=edgeInfo[0]
      if roadName.find('280') >= 0:
        matches[v1][v2] = edgeInfo
  info('%d edges in G contain 280' % len(matches))
  return matches

def isHighwayEdge(edge):
  name=edge[NAME]
  for s in ['280','101','ON RAMP','I-80','HWY']:
    if name.find(s) >= 0:
      return True
  return False

# 'road','I-280 SOUTHBOUND',-0.059507...
@timed
def removeHighwayEdgesFromGraph(inputFile,outputFile=NO_HIGHWAY_GRAPH):
  info('Removing highway edges from graph')
  oldGraph=load(inputFile)
  nExcluded=0
  newGraph={}
  for v1 in oldGraph:
    for v2 in oldGraph[v1]:
      edgeInfo=oldGraph[v1][v2]
      if isHighwayEdge(edgeInfo):
        nExcluded += 1
      else:
        if v1 in newGraph:
          newGraph[v1][v2]=edgeInfo
        else:
          newGraph[v1]={v2:edgeInfo}
  save(newGraph,outputFile)
  info('Done.  Excluded %d edges from graph.' % nExcluded)

@timed
def makeNewXY():
  newGraph=load(NO_HIGHWAY_GRAPH)
  ptsXY={}
  ptsYX={}
  for v in newGraph:
    pt=strPtToFloatPt(v)
    ptsXY[pt]=1
    ptsYX[(pt[1],pt[0])]=1
  sortedXY=ptsXY.keys()
  sortedYX=ptsYX.keys()
  sortedXY.sort()
  sortedYX.sort()
  save(sortedXY,PTS_XY)
  save(sortedYX,PTS_YX)

if __name__ == '__main__':
  removeHighwayEdgesFromGraph(GRAPH)
  makeNewXY()
