# generate_final_data.py
#
# generate the final set of data structures used by bike map

import common
import ConfigParser, logging, os, cPickle, math
from logging import debug, info, warning, error, critical
from os.path import join, exists, splitext
from bisect import bisect_left
from collections import defaultdict

def generate_dGraph():
   """
   generates dGraph:
      dGraph[fromCNN][toCNN] = [{'STREET':sStreet, 'INCLINE':nIncline, 'TYPE':sType, 'CNN':sCNN}]
   """
   dEdgeInfo = common.load_pickle('BikeData/dEdgeInfo.pkl')
   dOrientations = common.load_pickle('BikeData/dOrientations.pkl')
   
   # experimentally it looks like only a few edge cnns have no orientation
   # those will be 2 way - bad, if it leads to paths that abruptly 'end'
   # because the path is actually 1way but started off 2 way
   
   #-1 = TO -> FROM
   #1  = FROM -> TO
   #2  = both
   dGraph = {}
   nEdges = 0
   global lMultiplyDefinedEdges
   lMultiplyDefinedEdges = []
   for fromCNN in dEdgeInfo:
      for toCNN in dEdgeInfo[fromCNN]:
         lEdgeInfo = dEdgeInfo[fromCNN][toCNN]
         if len(lEdgeInfo) > 1:
            lMultiplyDefinedEdges.append({'FROM':fromCNN, 'TO':toCNN, 'COUNT':len(lEdgeInfo), 'INFO':lEdgeInfo})
         for edgeInfo in lEdgeInfo:
            edgeInfo['INCLINE'] = 0 # set this up as dummy value till heights get added
            edgeCNN = edgeInfo['CNN']
            orientation = '2' # default is 2 way
            if edgeCNN in dOrientations:
               orientation = dOrientations[edgeCNN]
               if orientation not in ['-1', '1', '2']:
                  error('Invalid orientation %s, type %s' % (orientation, str(type(orientation))))
                  orientation = '2'
            if orientation == '-1' or orientation == '2':
               addEdge(dGraph, toCNN, fromCNN, edgeInfo)
            elif orientation == '1' or orientation == '2':
               addEdge(dGraph, fromCNN, toCNN, edgeInfo)
            
   common.save_pickle(dGraph, r'BikeData/Graph.pkl')
   
   info("Done building dGraph.  %d keys" % len(dGraph))

def getMissingNodeList():
   G = common.load_pickle('BikeData\\Graph.pkl')
   info('Loaded G, %d keys' % len(G))
   dNodeInfo = common.load_pickle('BikeData\\dNodeInfo.pkl')
   info('Loaded dNodeInfo, %d nodes' % len(dNodeInfo))
   missing = []
   for x in G:
      for y in G[x]:
         if x not in dNodeInfo and x not in missing:
            missing.append(x)
         if y not in dNodeInfo and y not in missing:
            missing.append(y)
   return missing
  

def fixMissingNodes():
   """
   find all nodes in G that aren't in dNodeInfo
   then for as many as possible, see if their info can be deduced
   """
   G = common.load_pickle('BikeData\\Graph.pkl')
   info('Loaded G, %d keys' % len(G))
   dNodeInfo = common.load_pickle('BikeData\\dNodeInfo.pkl')
   info('Loaded dNodeInfo, %d nodes' % len(dNodeInfo))
   missing = []
   for x in G:
      for y in G[x]:
         if x not in dNodeInfo and x not in missing:
            missing.append(x)
         if y not in dNodeInfo and y not in missing:
            missing.append(y)
   info('Found %d nodes in G that are missing from dNodeInfo.  Fixing...' % len(missing))
   sts = common.load_pickle('PickledGISData\stclines_streets_wgs.pkl')
   d = defaultdict(list)
   for st in sts:
      fromcnn = str(st['F_NODE_CNN'])
      tocnn = str(st['T_NODE_CNN'])
      if fromcnn in m:
             d[fromcnn].append(st)
      if tocnn in m:
             d[tocnn].append(st)
   # now fill in nodes with street list and coords (pt)
   # {'STREETS': ['24TH AVE', 'ORTEGA ST'], 'COORDS': (-122.4817021076317, 37.752140003057157)}
   nFixed = 0
   for node in missing:
      edges = d[node]
      if len(edges) > 1:
         nFixed += 1
         lPts = []
         lStreet = []
         ptToUse = None
         for edge in edges:
            # gather street names associated with this node's intersection
            stname = edge['STREET'] + " " + edge['ST_TYPE']
            if not stname in lStreet:
               lStreet.append(stname)
            # if we can find a pt the different edges using this node
            # all share, use the shared pt
            for pt in edge['COORDS']:
               if pt in lPts:
                  ptToUse = pt
               else:
                  lPts.append(pt)
            # if none of the edges using this node share a pt, find
            # the closest pair and pick one arbitrarily
            if ptToUse == None:
               mindist = sys.maxint
               for i in range(0, len(lPts)):
                  for j in range(i+1, len(lPts)):
                     dist = common.distance(lPts[i], lPts[j])
                     if dist < mindist:
                        mindist = dist
                        ptToUser = lPts[i]
         if len(sts) < 2:
            error("Len streets less than two for node %s" % node)
         if ptToUse == None:
            error("PtToUse is none for node %s" % node)
         dNodeInfo[node] = {'STREETS':lStreet, 'COORDS':ptToUse}
   info('Fixed %d items.  Going in for 2nd pass...' % nFixed)
   missing = []
   for x in G:
      for y in G[x]:
         if x not in dNodeInfo and x not in missing:
            missing.append(x)
         if y not in dNodeInfo and y not in missing:
            missing.append(y)
   info('Attempting to fix %d remaining missing nodes' % len(missing))
   nFixed = 0
   for x in G:
      for y in G[x]:
         edgeinfo = G[x][y]
         if y in missing and x not in missing:
            xcoord = dNodeInfo[x]['COORDS']
            lcoords = []
            lcoords.append(edgeinfo['COORDS'][0])
            lcoords.append(edgeinfo['COORDS'][len(edgeinfo['COORDS'])-1])
            newcoord = None
            if xcoord in lcoords:
               lcoords.remove(xcoord)
               if len(lcoords) > 1:
                  error('Multiple coords remaining, will just go with first')
               newcoord = lcoords[0]
               lsts = [edgeinfo['STREET']]
               dNodeInfo[y] = {'STREET':lsts, 'COORDS':newcoord}
               nFixed += 1
            else:
               error('G[%s][%s] - xcoord is %s but not found in edgeinfo coord list %s' % (x,y,xcoord,str(lcoords)))
         elif x in missing and y not in missing:
            ycoord = dNodeInfo[y]['COORDS']
            lcoords = []
            lcoords.append(edgeinfo['COORDS'][0])
            lcoords.append(edgeinfo['COORDS'][len(edgeinfo['COORDS'])-1])
            newcoord = None
            if ycoord in lcoords:
               lcoords.remove(ycoord)
               if len(lcoords) > 1:
                  error('Multiple coords remaining, will just go with first')
               newcoord = lcoords[0]
               lsts = [edgeinfo['STREET']]
               dNodeInfo[x] = {'STREET':lsts, 'COORDS':newcoord}
               nFixed += 1
            else:
               error('G[%s][%s] - ycoord is %s but not found in edgeinfo coord list %s' % (x,y,ycoord,str(lcoords)))
   info('Fixed an additional %d items' % nFixed)
   common.save_pickle(dNodeInfo, 'BikeData\\dNodeInfo.pkl')
   info('Saved dNodeInfo, %d nodes.' % len(dNodeInfo))
                  

def addEdge(dGraph, node1, node2, edgeInfo):
   """
   addEdge(G, node1, node2, edgeInfo)
   assume for now we just insert 'INCLINE':0 into edge info
   """
   if 'INCLINE' not in edgeInfo:
      edgeInfo['INCLINE'] = 0
   if node1 in dGraph:
      if node2 not in dGraph[node1]:         
         dGraph[node1][node2] = edgeInfo
   else:
      dGraph[node1] = {node2:edgeInfo}
   
def generate_dPtToNodeCNN():
   lDupes = []
   dNodeInfo = common.load_pickle('BikeData//dNodeInfo.pkl')
   # NODE CNN -> {'COORDS': pt, 'STREETS':list of st}
   dPtToNodeCNN = {}
   for node in dNodeInfo:
      pt = dNodeInfo[node]['COORDS']
      if pt in dPtToNodeCNN:
         lDupes.append[(node,dPtToNodeCNN[pt],pt)]
      dPtToNodeCNN[pt] = node
   if len(lDupes) > 0:
      error('Warning, %d pts map to the same Node CNN' % len(lDupes))
      i = 0
      for node1, node2, pt in lDupes:
         debug('%d. %s %s both map to pt %s\n' % (i, node1, node2, pt))
         i += 1
   common.save_pickle(dPtToNodeCNN, r'BikeData/dPtToNodeCNN')
   info("Done building dPt, %d keys" % len(dPtToNodeCNN))
   
def generate_dNode():
   info("not ready")
   


def generate_dCorner():
   """
   generate_dCorner():

   generates a dictionary of all pairs of streets that intersect at a node.
   no duplicates are stored!  choice between dupes is made using criteria
   x <= y, e.e. Aardvark St & Zebra St will always be a pair, never Zebra
   & Aardvark.  dictionary maps street pairs to node CNN
   """
   dCorner = {}
   dNodeInfo = common.load_pickle("BikeData\\dNodeInfo.pkl")
   for node, info in dNodeInfo.iteritems():
      lSts = info['STREETS']
      lSts.sort()
      for x in range(0, len(lSts)-1): # for a, b, c, d would give 0, 1, 2
         for y in range(x+1, len(lSts)): # for a,b,c,d and x=0, would give 1, 2, 3
            dCorner['%s,%s' % (lSts[x], lSts[y])] = {'COORDS':info['COORDS'], 'NODE':node}
   common.save_pickle(dCorner, "BikeData\\dCorner.pkl")
   debug("Generated dCorner, %d entries" % len(dCorner))
   
def generate_lPt():
   info("not ready")

def generate_lStreet():
   dCorner = common.load_pickle('BikeData\\dCorner.pkl')
   lSts = []
   for stPair in dCorner:
      for st in stPair.split(','):
         i = bisect_left(lSts, st)
         # avoid dupes
         if i < len(lSts)-1 and lSts[i] == st:
            pass
         else:
            lSts.insert(i, st)
         
   common.save_pickle(lSts, "BikeData\\lStreet.pkl")
   debug("Generated lStreet, %d entries" % len(lSts))

def updateBikeEdgesWithCNN():
   """
   for each edge in G, updates with bike path type
   if edge is a bike path with CNN
   """
   dBikeEdges = common.load_pickle('BikeData\\dBikeEdges.pkl')
   G = common.load_pickle('BikeData\\Graph.pkl')
   nUpdated = 0
   for v1 in G:
      for v2 in G[v1]:
         edgecnn = G[v1][v2]['CNN']
         if edgecnn in dBikeEdges:
            G[v1][v2]['TYPE'] = dBikeEdges[edgecnn]
            nUpdated += 1
   common.save_pickle(G, 'BikeData\\Graph.pkl')
   info('Updated %d entries in G' % nUpdated)

def fixBikeEdgesNoCNN():
   """
   for bike edges with NO info except coords, creates a new edge.
   sets from/to cnn to closest match in dNodeCNN
   """

def create_all_datasets():
   incremental = common.config.get('general', 'incremental')
   if not exists('BikeData//Graph.pkl') or incremental != 'True':
      generate_dGraph()
   if not exists('BikeData//dCorner.pkl') or incremental != 'True':
      generate_dCorner()
   if not exists('BikeData//dPtToNodeCNN.pkl') or incremental != 'True':
      generate_dPtToNodeCNN()
   if not exists('BikeData//lStreet.pkl') or incremental != 'True':
      generate_lStreet()
   fixMissingNodes()
   updateBikeEdgesWithCNN()
   """        
   # experimentally it looks like only a few edge cnns have no orientation
   # those will be 2 way
   # bad though if it leads to starting down a path that abruptly 'ends' because
   # path is actually 1way but looks like it starts off 2 way
   #lEdgeCNNNoOrient = count_missing_cnns(d, 'dEdgeCNNTo1', 'dOrientations')
   #lOrientNoEdgeCNN = count_missing_cnns(d, 'dOrientations', 'dEdgeCNNTo1')
   
   -1 = TO -> FROM
   1  = FROM -> TO
   2  = both
   """
   d = common.load_all_pickled_files(common.sBikeDataDir)
   

############ MAIN ################
# just for testing, no validation
# use generate_data
#
if __name__ == "__main__":

   os.chdir(os.getcwd())
   common.load_config_file_and_setup_logging()
   #create_all_datasets()

   #d = common.load_all_pickled_files(common.sBikeDataDir)
   #info('Done.  %d datasets available in d: %s' % (len(d), d.keys()))


   
