#!/usr/bin/python
# generate_data.py
#
# kicks off everything else

import common
import convert_gis_data
import create_intermediate_structures
import create_final_structures

import ConfigParser, logging, os
from logging import debug, info, warning, error, critical

############ MAIN ################
            
if __name__ == "__main__":

   os.chdir(os.getcwd())
   common.load_config_file_and_setup_logging()

   try:
      nStartStep = config.get('general', 'step')
   except:
      nStartStep = 1

   """
   1. Convert GIS data sets to pickled lists of rows
   """
   if nStartStep <= 1:
      convert_gis_data.convert_all_datasets()

   """
   2. Create intermediate structures:
      dNodeInfo.pkl
      dOldEdgeInfo.pkl
      dNewEdgeInfo.pkl
      dOrientations.pkl
      dPtToHeight.pkl
      dBikeEdgeInfo.pkl
      lBikeEdgesNoCNN.pkl     
   
      we have intermediate structures so we can regenerate a given structure
      without regenerating EVERYTHING
   """
   if nStartStep <= 2:
      create_intermediate_structures.create_all_datasets()

   """
   3. Create final structures:
      Graph.pkl - dict[nodeCNN][nodeCNN] -> edgeinfo
                  edgeinfo is dict with, at minimum, 'incline', 'street', 'type'
                  TODO: what if there are multiple edges connecting two nodes?
      dPt - maps pts to node CNN, height, etc
      dNode - maps node CNN to pt
      dCorner - maps corner to node CNN, pt
      lPt - pts in graph, sorted     
      lStreet - street names in graph, sorted
   """
   if nStartStep <= 3:
      create_final_structures.create_all_datasets()
      
   info('Done')
   
