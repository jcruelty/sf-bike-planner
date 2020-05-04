"""
generate_elevation_map.py

Copyright 2008 Amar Pai

If this code is used you must credit me and keep it under an open source
license (freely redistributable/modifiable under these same terms)

Given SF contour map shapefile, generates two pickle files:

elevation_tuples.pkl 
sorted_elevation_tuples.pkl

Both are lists of elevation tuples where elevation tuple is:
(float x, float y, float elevation)

Pickling is done with protocol 2 (most efficient)
"""


from common import *

import shapelib, dbflib, os, cPickle

from os.path import join, exists, splitext, abspath

def generate_elevation_map():
    """
    INPUT: contour map consisting of records
        OBJECTID ISOLINE_TY ELEVATION SHAPE_LEN
        + set of points
    OUTPUT: list of (lat,long,elevation) 
    """
    tuples = []
    shp = shapelib.ShapeFile(CONTOUR_SHPFILE)
    dbf = dbflib.DBFFile(CONTOUR_DBFFILE)
    num_records = dbf.record_count()
    interval = num_records / 50
		multiple_vertex_lists = []
    info('Opened %s\n%d records to process... ' % (CONTOUR_SHPFILE, num_records))
    for i in range(0, num_records):
        # Fields:
        #
        # SHAPE__Len    float   1590.08208442
        # ELEVATION     float   0.0
        # OBJECTID      int     2
        # ISOLINE_TY    str     "800 - Normal"
        #
        rec = dbf.read_record(i)
        elevation = float(rec['ELEVATION'])
        obj = shp.read_object(i)
        # TODO is there ever more than one item in obj.vertices() ?
				vertices = obj.vertices()
				if len(vertices) > 1:
					#rec['VERTICES'] = vertices
					rec['NUM_VERTEX_LISTS'] = len(vertices)
					multiple_vertex_lists.append(rec)
					vertices = vertices[0]
				vertices = obj.vertices()[0]
        # each vert is (float,float)
        for vert in vertices:
            assert type(vert[0]) == type(vert[1]) == float
            tuples.append((vert[0], vert[1], elevation))
        if i % interval == 0:
            info("%d " % i)
            
    info('Done.\nOutput list contains %d points each' % len(tuples))
		info('%d items with multiple vertex lists' % len(multiple_vertex_lists))
		save(multiple_vertex_lists, outputFileName("/multiple_vertex_lists.pkl"))
    save(tuples, ELEVATION_TUPLES)
    print 'Sorting... ',
    tuples.sort()
    print 'Done'
    save(tuples, outputFileName("elevation_xy.pkl"))
		tuples = [(y, x, elevation) for x,y,elevation in tuples]
		tuples.sort()
		save(tuples, outputFileName("elevation_yx.pkl"))
    
############ MAIN ################
# just for testing purposes, so not a lot of validation.
# generate_data.py has all the heavy duty validation.

if __name__ == "__main__":
   generate_elevation_map()
   
