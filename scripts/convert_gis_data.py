"""
convert_gis_data.py

Copyright 2006 Amar Pai

If this code is used you must credit me and keep it under an open source
license (freely redistributable/modifiable under these same terms)

This script looks in the GIS data directory for shapefiles.
For each shapefile it creates a corresponding pickled Python structure-
list of dict, where each dict is a set of key/value pairs.  The list of
dicts is the set of "rows" in the GIS data set described by the shapefile.

Assumes associated files are in the same dir.

Pickling is done with protocol 1.
"""
from common import *
import shapelib, dbflib

def convert_gis_dataset(sDataSet, sInputDir, sOutputDir):
    """
    convert_gis_dataset(sDataSet, sInputDir, sOutputDir)

    Convert a shapefile to a pickled data structure (list of dicts representing rows of data)
    Writes pkl file to sOutputDir.
    Assumes sDataSet.shp, sDataSet.dbf, etc. are all present in sInputDir.  TODO: verify this
    Each row in the pickled data structure will have an extra key, 'COORDS',
    with value = a single point (pair of floats) or a list of points.
    """
    info("loading %s" % sDataSet)
    
    basePa= join(sInputDir, sDataSet)

    debug("shpfile path is %s" % sBasePath + ".shp")
    shp = shapelib.ShapeFile(sBasePath + ".shp")
    dbf = dbflib.DBFFile(sBasePath + ".dbf")
    nRecords = dbf.record_count()
    nProgressInterval = nRecords / 10 # show progress in increments of 10%
    lRows = []
    print 'Progress: ',
    for i in range(0, nRecords):
        if i % nProgressInterval == 0:
            print " %.2f " % (float(i) / float(nRecords)),
        rec = dbf.read_record(i)
        obj = shp.read_object(i)
        verts = obj.vertices()
        # we can probably remove this check if no alarms go off, but for now be safe   
        if len(verts) > 1:
            rec['ALLCOORDS'] = verts
            rec['COORDS'] = verts[0]
        else:
            rec['COORDS'] = verts[0]
        lRows.append(rec)
    print '\n'
    sOutputPath = join(sOutputDir, sDataSet + ".pkl")
    f = open(sOutputPath, 'wb')
    cPickle.dump(lRows, f, 1)
    f.close()
    info("created %s.  %d rows." % (sOutputPath, len(lRows)))

def convert_all_datasets():
    """
    convert_all_datasets(sInputDir, sOutputDir)

    Runs convert_gis_dataset on every shapefile in sInputDir.
    Assumes that if a .shp file is present, all the associated files (.dbf, etc) are also present.
    TODO: verify this.
    """
    print 'outputdir = ' + sPickledGISDir
    for subdir in lGISDirs:
        print 'processing ' + subdir
        lFiles = os.listdir(subdir)
        for sFileName in lFiles:
            sRoot, sExt = splitext(sFileName)
            if sExt == ".shp":
                convert_gis_dataset(sRoot, subdir, sPickledGISDir)
        
############ MAIN ################
# just for testing purposes, so not a lot of validation.
# generate_data.py has all the heavy duty validation.

if __name__ == "__main__":
    print "working dir is " + os.getcwd()
    os.chdir(os.getcwd())
    common.load_config_file_and_setup_logging()
    convert_all_datasets() 
    #dUnpickled = common.load_all_pickled_files(sPickledGISDir)
    #info('Done.  %d datasets available in dUnpickled' % len(dUnpickled))
    
