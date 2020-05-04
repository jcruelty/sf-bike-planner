"""
create_intermediate_structures.py

Copyright 2006 Amar Pai

If this code is used you must credit me and keep it under an open source
license (freely redistributable/modifiable under these same terms)

This script takes pickled GIS datasets and generates data structures
that provide  useful 'views' on the data.  The generated primary data structures
can then be used to generate secondary data structures that are used by the bike
map.  Secondary data structures values will be 'massaged', 'processed', 'fixed', etc,
whereas primary data structures should be straight mappings from the original GIS
data.  That way problems in secondary data can be corrected without having to
regenerate primary data if problems occur.
"""

import common
import os, cPickle
from logging import debug, info, warning, error, critical
from os.path import join, exists, splitext
from bisect import bisect_right, insort_right

def generate_dNodeInfo(lRows, sOutputPath):
    """
    generate_dNodeInfo(lRows, sOutputPath)

    Generated pickled file:
    dNodeInfo = dict mapping node CNN to node info
                node info = {'COORDS': pt, 'STREETS':list of st}

    stintersections_wgs.pkl contains 18391 rows. Keys:
    CNNTEXT              type: <type 'str'>         e.g: 53005000
    OBJECTID             type: <type 'int'>         e.g: 1
    ST_TYPE              type: <type 'str'>         e.g: 
    COORDS               type: <type 'tuple'>       e.g: (-122.4837368666856, 37.720691450743779)
    CNN                  type: <type 'float'>       e.g: 53005000.0
    ST_NAME              type: <type 'str'>         e.g: UNNAMED 113
    """
    dNodeInfo = {}
    nRows = len(lRows)
    nProgressInterval = nRows / 10 # show progress in increments of 10%
    info('Progress:')
    for i, row in enumerate(lRows):
        if i % nProgressInterval == 0:
            print " %.2f " % (float(i) / float(nRows)),
        sStreet = row['ST_NAME'].strip()
        sType = row['ST_TYPE'].strip()
        if sType:
            sStreet += " " + sType
        sCNN = row['CNNTEXT'].strip()
        pt = row['COORDS']
        if sCNN not in dNodeInfo:
            dNodeInfo[sCNN] = {'COORDS':pt, 'STREETS':[sStreet]}
        else:
            if pt != dNodeInfo[sCNN]['COORDS']:
                error('NodeCNN %s has conflicting pt values %s and %s. \
                       Object id: %s' % (sCNN, pt, pt, row['OBJECTID']))
            else:
                if sStreet in dNodeInfo[sCNN]['STREETS']:
                    error('NodeCNN %s has multiple rows with same st name %s. \
                          Object id = %s', (sCNN, sStreet, row['OBJECTID']))
                else:
                     dNodeInfo[sCNN]['STREETS'].append(sStreet) 
    print '\n'
    common.save_pickle(dNodeInfo, sOutputPath)
    info('Done')

def generate_dEdgeInfo(lRows, sOutputPath):
    """
    generate_dEdgeInfo(lRows, sOutputPath)
    
    Generates pickled file:
    dEdgeInfo - dict mapping fromcnn/tocnn to list of edge info
                edge info = {'COORDS':lPt, 'STREET':sStreet, 'CNN':sEdgeCNN, 'OBJECTID':sObjectId, 'TYPE':sType}

    NOTE: some streets are dead ends, thus their ToCNN won't be in list generated
    by process_stintersections.  TODO : massage to account for this
    
    stclines_streets_wgs.pkl contains 15623 rows. Keys:
    LF_FADD              type: <type 'float'>       e.g: 41.0
    LAYER                type: <type 'str'>         e.g: STREETS
    ACCEPTED             type: <type 'str'>         e.g: Y
    DISTRICT             type: <type 'str'>         e.g: 10
    OBJECTID             type: <type 'int'>         e.g: 2
    ST_TYPE              type: <type 'str'>         e.g: ST
    CNNTEXT              type: <type 'str'>         e.g: 15107000
    F_NODE_CNN           type: <type 'int'>         e.g: 20013000
    RT_FADD              type: <type 'float'>       e.g: 34.0
    SHAPE__Len           type: <type 'float'>       e.g: 132.296611069
    JURISDICTI           type: <type 'str'>         e.g: DPW
    LF_TOADD             type: <type 'float'>       e.g: 99.0
    STREET               type: <type 'str'>         e.g: GILROY
    COORDS               type: <type 'list'>        e.g: [(-122.38897780258986, 37.716086985221892), (-122.38923758561893, 37.715787946643296)]
    CNN                  type: <type 'float'>       e.g: 15107000.0
    T_NODE_CNN           type: <type 'int'>         e.g: 51652000
    RT_TOADD             type: <type 'float'>       e.g: 98.0
    NHOOD                type: <type 'str'>         e.g: Bayview Heights
    STREETNAME           type: <type 'str'>         e.g: GILROY ST
    ZIP_CODE             type: <type 'str'>         e.g: 94124
    """
    dEdgeInfo = {}
    nRows = len(lRows)
    nProgressInterval = nRows / 10 # show progress in increments of 10%
    info('Progress:')
    for i, row in enumerate(lRows):
        if i % nProgressInterval == 0:
            print " %.2f " % (float(i) / float(nRows)),
        # TODO : strip newlines etc?
        # save for secondary; have 'prettify st name' function
        sStreet = row['STREET'].strip()
        sType = row['ST_TYPE'].strip()
        if sType:
            sStreet += " " + sType
        sEdgeCNN = row['CNNTEXT'].strip()
        sFromCNN = '%d' % row['F_NODE_CNN'] 
        sToCNN = '%d' % row['T_NODE_CNN']
        sObjectId = '%d' % row['OBJECTID']
        lPt = row['COORDS']
        if sStreet != row['STREETNAME'].strip():
            error('Conflicting values STREET = %s, ST_TYPE = %s, STREETNAME = %s for EdgeCNN %s.  ObjectId = %s' %
                  (row['STREET'], row['ST_TYPE'], row['STREETNAME'], sEdgeCNN, sObjectId))
        edgeInfo = {'COORDS':lPt, 'STREET':sStreet, 'CNN':sEdgeCNN, 'OBJECTID':sObjectId, 'TYPE':'road'}
        if sFromCNN in dEdgeInfo and sToCNN in dEdgeInfo[sFromCNN]:
            dEdgeInfo[sFromCNN][sToCNN] = edgeInfo
        else:
            if sFromCNN in dEdgeInfo:
                dEdgeInfo[sFromCNN][sToCNN] = edgeInfo
            else:
                [sFromCNN] = {sToCNN:edgeInfo}
    print '\n'
    common.save_pickle(dEdgeInfo, sOutputPath)
    info('Done')

def process_dpt_bike_network(lRows, dEdgeInfo, sOutputDir):
    """
    process_dpt_bike_network(lRows, sOutputPath)
    Generates pickled files:
        dBikeEdgeInfo - dict mapping edge cnn to list of edge info
            edge info = {'COORDS':lPt, 'STREET':sStreet, 'CNN':sEdgeCNN, 'OBJECTID':sObjectId, 'TYPE':sType}
        lBikeEdgesMissingInfo - list of rows that didn't have a cnn in dEdgeInfo
        
    dpt_bike_network_wgs.pkl contains 2340 rows. Keys:
    LAYER                type: <type 'str'>         e.g: STREETS
    OBJECTID             type: <type 'int'>         e.g: 1
    FACILITY_T           type: <type 'str'>         e.g: bike path
    SHAPE__Len           type: <type 'float'>       e.g: 480.957433585
    NUMBER               type: <type 'str'>         e.g: 
    TO_ST                type: <type 'str'>         e.g: LAGUNA ST
    COORDS               type: <type 'list'>        e.g: [(-122.43004499669473, 37.803517817967595), (-122.43167936892718, 37.803266735581644)]
    CNN                  type: <type 'str'>         e.g: 2788000
    FROM_ST              type: <type 'str'>         e.g: OCTAVIA ST
    TYPE                 type: <type 'str'>         e.g: ST
    ID                   type: <type 'int'>         e.g: 3270
    STREETNAME           type: <type 'str'>         e.g: BAY
    """
    dEdgeCNNTo1 = {}
    for fromCNN in dEdgeInfo:
        for toCNN in dEdgeInfo[fromCNN]:
            for edge in dEdgeInfo[fromCNN][toCNN]:
                dEdgeCNNTo1[edge['CNN']] = 1

    dRank = {'bike path':4, 'bike lane':3, 'bike route':2, 'wide curb lane':1, 'road':0}
    
    dBikeEdgeInfo = {}
    lBikeEdgesNoCNN = []
    nRows = len(lRows)
    nProgressInterval = nRows / 10 # show progress in increments of 10%
    info('Progress:')
    for i, row in enumerate(lRows):
        if i % nProgressInterval == 0:
            print " %.2f " % (float(i) / float(nRows)),
        sFacilityType = row['FACILITY_T'].strip()
        sCNN = row['CNN'].strip()
        sObjectId = '%s' % row['OBJECTID']
        if sCNN in dEdgeCNNTo1:
            if sCNN not in dBikeEdgeInfo:            
                dBikeEdgeInfo[sCNN] = sFacilityType
            else:
                sOldType = dBikeEdgeInfo[sCNN]
                if dRank[sFacilityType] > dRank[sOldType]:
                    dBikeEdgeInfo[sCNN] = sFacilityType         
        else:
            lBikeEdgesNoCNN.append(row)
    print '\n'
    common.save_pickle(dBikeEdgeInfo, join(sOutputDir, 'dBikeEdges.pkl'))
    common.save_pickle(lBikeEdgesNoCNN, join(sOutputDir, 'lBikeEdgesNoCNN.pkl'))
    info('Done')
 
    
def generate_dPtToHeight(sInputPath, sOutputPath):
    """
    generate_dPtToHeight(sInputPath, sOutputDir)
    
    Takes a text file (tab separated) obtained by "trimming"
    contour map.
    TODO find a better way
    Generates:
        dPtToHeight - dict of pt to elevation in feet (float)
    phys_contours: OBJECTID ELEVATION ISOLINE_TY SHAPE__Len     arcs corresponding to elevation contours
    text file:
    id  x                y              z       m     objid     elevation       isoline type    shape_len                        
    2	-122.36531222	 37.72557844	0	0	1	-25.00000000	800 - Normal	2.40518476701e+003	
    """    
    dPtToHeight = {}
    f = open(sInputPath)
    lRows = f.readlines()
    f.close()
    nRows = len(lRows)
    nProgressInterval = nRows / 100 # show progress in increments of 10%
    info('Progress:')
    for i, row in enumerate(lRows):
        if i % nProgressInterval == 0:
            print " %.2f " % (float(i) / float(nRows)),
        values = row.split('\t')
        sX, sY, sHeight = values[1].strip(), values[2].strip(), values[6].strip()
        if len(sX) == 0 or len(sY) == 0 or len(sHeight) == 0:
            error('%s had 0 length x, y or height' % str(row))
        else:
            dPtToHeight[(float(sX),float(sY))] = float(sHeight)
    print '\n'
    common.save_pickle(dPtToHeight, sOutputPath)

def generate_dOrientations(sInputPath, sOutputPath):
    """
    generate_dOrientations(sInputPath, sOutputPath)

    This one is a bit different because it takes a txt file, not shp/dbf.
    Generates:
        dOrientation - dict of edgecnn to 2/1/-1
    
    sts_1way.csv: OBJECTID CNN ONEWAY
    2, -1, 1 are possible values
    CNN corresponds to street arc CNNs
    """    
    dOrientation = {}
    f = open(sInputPath)
    lRows = f.readlines()
    f.close()
    nRows = len(lRows)
    nProgressInterval = nRows / 10 # show progress in increments of 10%
    info('Progress:')
    for i, row in enumerate(lRows):
        if i % nProgressInterval == 0:
            print " %.2f " % (float(i) / float(nRows)),
        sObjectId, sCNN, sOneWay = row.split(',')
        dOrientation[sCNN] = sOneWay.strip()
    print '\n'
    common.save_pickle(dOrientation, sOutputPath)

def create_all_datasets():
    """
    create_all_datasets(sInputDir, sOutputDir)

    Runs creation functions for all required GIS data sets.
    Throws exception if a given data set is not found.
    """
    # generate dNodeInfo, dOldEdgeInfo, dOrientations, dPtToHeight
    dUnpickled = common.load_all_pickled_files(common.sPickledGISDir)
    os.chdir(common.sBikeDataDir)
    generate_dNodeInfo(dUnpickled['stintersections_wgs'], 'dNodeInfo.pkl')
    generate_dEdgeInfo(dUnpickled['stclines_streets'],  'dOldEdgeInfo.pkl')
    generate_dEdgeInfo(dUnpickled['stclines_streets_wgs'],  'dNewEdgeInfo.pkl')
    generate_dOrientations('..\GISData\\sts_1way.txt', 'dOrientations.pkl')
    generate_dPtToHeight('..\GISData\\contours10.txt', 'dPtToHeight.pkl')

    # generate dBikeEdgeInfo, lBikeEdgesNoCNN
    # looks like old edge info has more matching CNNs
    dOldEdgeInfo = common.load_pickle('dOldEdgeInfo.pkl')
    dNewEdgeInfo = common.load_pickle('dNewEdgeInfo.pkl')
    process_dpt_bike_network(dUnpickled['dpt_bike_network_wgs'], dOldEdgeInfo, "BikeMapData")

    # Result of testing: all dOldEdgeInfo nodes are in dNodeInfo
    # Some new dEdgeInfo nodes are missing from dNodeInfo
    # So probably better to use dOldEdgeInfo when building graph?

    info('Done')
    
        
	
############ MAIN ################
# just for testing, not a lot of validation
if __name__ == "__main__":
    
    common.load_config_file_and_setup_logging(os.getcwd())

    """   
    create_all_datasets()

    d = common.load_all_pickled_files(common.sBikeDataDir)
    info('Done.  %d datasets available in d: %s' % (len(d), d.keys()))
    """
