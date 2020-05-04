#!/usr/bin/python

from common import *
import minjson
from bisect import bisect, insort_right

loaded=False
G={}
uniquePts=[]

"""
bike route:     an unstriped, signed roadway shared by bicycles and motorized vehicles.
wide curb lane: a bike route's right-hand traffic lane that is wide enough to accommodate bicycles and motorized vehicles side by side in the same lane. (This is not a striped bike lane.)
bike lane:      a part of the roadway which is striped and signed for bicycles only. On this plan, only rural roads have striped bike lanes.
bike path:      an off-road paved trail for bicycles.
"""

# default values; can be overridden by user
multipliers = {'bike path':1.0, 
               'bike lane':1.0, 
               'wide curb lane':1.0, 
               'bike route':1.0, 
               'road':1.0,
               'turn':1.0} # TODO : figure out if turn multiplier makes sense
maxGrade = 999.0

#presets
mostBikeFriendly = {'wide curb lane':1.5, 'bike route':1.5, 'road':3.0}
balanced = {'bike lane':1.3, 'wide curb lane':1.5, 'bike route':1.5, 'road':1.6}
shortestPath = {}
presets = {'mostBikeFriendly':mostBikeFriendly, 'balanced':balanced, 'shortestPath':shortestPath}

def getWeight(pt1,pt2):
  edgeType = G[pt1][pt2][0]
  incline = G[pt1][pt2][2]
  if incline >= maxGrade:
    inclinePenalty = 500.0 # arbitrarily large number
  else:
    inclinePenalty = 1.0
  weight = (getDistance(pt1,pt2) * multipliers[edgeType]) * inclinePenalty

  return weight

# Dijkstra stuff
        
def initSingleSource(s):
  debug('initSingleSource %s' % s)
  for v in uniquePts:
    d[v] = float(1e3000)
    predecessor[v] = None
  d[s] = float(0.0)
  Q[float(0.0)] = [s]
  l.append(float(0.0))

def relax(u, v):
  weight = getWeight(u,v)
  if d[v] > (d[u] + weight):
    # if old d[v] is in l/Q, remove it
    if d[v] != float(1e3000): 
      i = bisect(l, d[v])
      if l[i-1] != d[v]:
        raise Exception("%s not same as %s in relax(%s, %s)" % (str(l[i-1]), str(d[v]), str(u), str(v)))
      del l[i-1]
      Q[d[v]].remove(v)
    d[v] = d[u] + weight
    # now add new d[v]
    insort_right(l, d[v])
    if d[v] in Q:
      Q[d[v]].append(v)
    else:
      Q[d[v]] = [v]
    predecessor[v] = u

def Dijkstra(w,s):
  debug('Dijkstra %s , %s' % (w,s))
  initSingleSource(s)
  while len(Q) > 0:
    minD = l.pop(0) # get distance of closest vertex to s
    u = Q[minD].pop(0)  # get first vertex in list of vertices at that distance
    if u == w:
      # print "Done"
      return # done!
    if u in G:
      for v in G[u]:
        # print 'processing edge ' + v + ' from vertex ' + u
        relax(u, v)
  #print "No path found"

@timed
def findRoute(pt1,pt2):
  global d,predecessor,Q,l
  # globals used by depth first search / breadth first search
  d = {}              # shortest paths by edge
  predecessor = {}    # precessor graph
  Q = {}              # dict of relaxed edge lengths -> [pt]
  l = []              # sorted list of relaxed edge lengths
  Dijkstra(pt2, pt1)
  if d[pt2] != float(1e3000):
    x = pt2
    path = []
    while x != pt1:
      path.insert(0, x)
      x = predecessor[x]
    path.insert(0, pt1)
    return path
  else:
    return None


# input: list of pts
# output: txt directions and minimal set of pts in path
#
def reducePath(path,html=True):
  debug("Reducing path\nInput:%s" % str(path))
  terminalPts,streetList,typeList,maxClimbList= [],[],[],[]
  totalDist = 0.0
  curStType,curStName,curMaxSlope=G[path[0]][path[1]]
  curStartPt=path[0]
  """
  start:spring&cali  end:1000 van ness
  edges in path: CALI CALI CALI HYDE HYDE VAN NESS
  desired output:
  Start: <inter>
  take CALI TO HYDE (st1 to st2)
  take HYDE TO VAN NESS (st2 to st3)
  take VAN NESS TO END (st3 to end)
  """
  indexOfLast=len(path)-1
  for i in range(0,indexOfLast):
    pt1 = path[i]
    pt2 = path[i+1]
    totalDist += getDistanceInFeet(pt1, pt2)
    edge = G[pt1][pt2]
    debug('Processing path[%d:%d] - G[%s][%s] - edge %s' % (i,i+1,pt1,pt2,edge))
    thisStType, thisStName, thisSlope=edge
    noMoreEdges = (i+1==indexOfLast)
    justTurned = (curStName!=thisStName)
    if justTurned or noMoreEdges:
      debug('Just turned or no more edges; adding to directions, maxClimb=%f' % curMaxSlope)
      terminalPts.append(curStartPt)
      streetList.append(curStName)
      typeList.append(curStType)
      maxClimbList.append(curMaxSlope)
      curStType,curStName,curMaxSlope=thisStType,thisStName,thisSlope
      curStartPt=pt1
    else:
      if thisSlope > curMaxSlope:
        curMaxSlope=thisSlope
  terminalPts.append(path[indexOfLast])
  outputStr = ""
  debug('Done.  len(streetList): %d\nlen(terminalPts): %d\n' % (len(streetList),len(terminalPts)))
  debug('Street list: %s\nTerminal pts: \n%s' % (streetList,terminalPts))
  indexOfLast=len(streetList)-1
  for i in range(0, len(streetList)):
    debug('%d: %s' % (i,streetList[i]))
    if i == indexOfLast:
      direction = "%d. Take %s to END." % (i+2, streetList[i])
    else:
      direction = "%d. Take %s to %s." % (i+2, streetList[i], streetList[i+1])
    pt1 = terminalPts[i]
    pt2 = terminalPts[i+1]
    dst = humanReadableFt(getDistanceInFeet(pt1, pt2))
    # <tr><td>TAKE X TO Y<td>DISTANCE<td>STEEPEST CLIMB<td>STREET TYPE</t>
    if html:
      outputStr += "<tr><td>%s<td>%s<td>%.2f<td>%s</tr>" % (
        direction, dst, maxClimbList[i], typeList[i])
    else:
      outputStr += "%s %s %.2f %s\n" % (
        direction.ljust(20), dst.ljust(20), maxClimbList[i], typeList[i].ljust(20))

  return outputStr, terminalPts, humanReadableFt(totalDist)

def initRoutePrefs(routePref,maxSlope):
  # set up multipliers and max grade (override previous values if any)
  global maxGrade,multipliers
  presetMultipliers = presets[routePref]
  for key in multipliers:
    multipliers[key] = presetMultipliers.get(key,1.0)
  maxGrade=float(maxSlope)
  debug('Route pref:%s\nMultipliers: %s\nMax grade: %f' % (routePref,str(multipliers),maxGrade))


def initGraph():
  # load global pkl structs, if not already done
  global G,uniquePts,loaded
  if not loaded:
    graphFile = (RUNNING_LOCALLY and GRAPH) or 'Graph.pkl'
    G=load(graphFile)
    uniquePts=getAllUniquePts(G)
    loaded=True

def initLogging(routingPref=None,maxSlope=None):
  if RUNNING_LOCALLY:
    setupLogging(logName='find_path',logLevel=logging.DEBUG)
 
def localGetDirections(fromAddy,toAddy,routePref='shortestPath',maxSlope=999.0):
  debug('getDirections')
  initRoutePrefs(routePref,maxSlope)
  
  info('Geocoding %s, %s' % (fromAddy,toAddy))
  fromResponse=geocode(fromAddy + ",san francisco,ca")
  toResponse=geocode(toAddy + ",san francisco,ca") 
  geocodedPt1='%f,%f' % (fromResponse['lon'],fromResponse['lat'])
  geocodedPt2='%f,%f' % (toResponse['lon'],toResponse['lat'])

  info('Finding closest graph pts to %s, %s' % (geocodedPt1,geocodedPt2))
  pt1=findClosestPoint(geocodedPt1,uniquePts,None)
  pt2=findClosestPoint(geocodedPt2,uniquePts,None)

  info("Finding route from %s to %s" % (pt1,pt2))
  path = findRoute(pt1, pt2)

  if not path:
    debug('Unable to find path between %s and %s' % (pt1, pt2))
    return None
  else:
    debug('Found route.  Raw path: %s' % str(path))

  debug("Getting directions")
  directions, minimalPath, totalDist = reducePath(path,html=False)
  debug('Minimal path:\n%s\nEnd step: %d' % ('\n'.join(minimalPath),len(minimalPath)+1))
  info('Directions:\n%sTotal dist: %s' % (directions,totalDist))

  return (directions,minimalPath,totalDist)

if __name__ == '__main__':
  initLogging()
  initGraph()
  if RUNNING_LOCALLY:
    if len(sys.argv) == 3:
        localGetDirections(sys.argv[1],sys.argv[2])
    else:
        localGetDirections('kearny st. and california', '1000 van ness')
        localGetDirections('spring st. and california', '1000 van ness')
  else:
    form = cgi.FieldStorage()
    errorMsg=""

    # inputs: routePref,maxSlope (optional)
    #         start,end (required)
    maxSlope=form.getvalue('maxSlope','999.0')
    routePref= form.getvalue('routePref','shortestPath')
    if not (routePref in presets):
      errorMsg+="%s is not a valid routePref<br>" % routePref
    else:
      initRoutePrefs(routePref,maxSlope)
    if not (form.has_key("start") and form.has_key("end")):
      # 16th and market to 24th and utah
      # pt1 = '-122.43307,37.76420', pt2 = '-122.40533,37.75306'
      # 1111 Minna to 7th and Irving
      pt1 = '-122.40928,37.77966'
      pt2 = '-122.46417,37.76413'
    else:
      pt1 = form.getvalue("start")
      pt2 = form.getvalue("end")

    # path finding
    if not errorMsg:
      startTime=time.time()
      path=findRoute(pt1,pt2)
      endTime=time.time()-startTime
      if not path:
        errorMsg = 'Unable to find path between %s and %s' % (pt1,pt2)

    # response
    result = {'method':'find_path'}
    result['error'] = (len(errorMsg)>0)
    if result['error']:
      result['msg'] = errorMsg
    else:
      directions,minimalPath,totalDist=reducePath(path)
      result['directions']=directions
      result['points']=path
      result['totalDist']=totalDist
      result['endStep']=len(minimalPath)+1
      result['time']="%.2f" % endTime

    finalMsg = "Content-Type: text/plain\n"   # TODO use application/json instead?
    finalMsg += 'Cache-Control: no-store, no-cache,  must-revalidate\n\n'
    finalMsg += minjson.write(result)
    print finalMsg

      

    
"""
def getPt2Intersect():
  if not os.path.exists(PT2INTERSECT):
    pt2intersect={}
    dNodeInfo=load(outputFilename('dNodeInfo.pkl'))
    dPointToNode=load(outputFilename('dPtToNodeCNN'))
    for pt in dPointToNode:
      pt2intersect[floatPtToStrPt(pt)]=dNodeInfo[dPointToNode[pt]] 
    save(pt2intersect,PT2INTERSECT)
  else:
    pt2intersect=load(PT2INTERSECT)
  return pt2intersect
"""

