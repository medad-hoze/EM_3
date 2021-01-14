# -*- coding: utf-8 -*-

import arcpy,math
import pandas as pd
import numpy as np
import uuid,json,datetime,sys,csv,os
from scipy.spatial import distance_matrix

arcpy.env.overwriteOutPut = True

from Basic_Tools        import *
from Engine_class       import Layer_Engine
    
print_arcpy_message('#  #  #  #  #     S T A R T     #  #  #  #  #')

# # # In Put # # #
DWGS        = [r"C:\GIS_layers\Vector\bad_DWG\14_1_2021\50552-1.dwg"]
#DWGS        = arcpy.GetParameterAsText(0).split(';')

# # #     Preper Data    # # #
scriptPath     = os.path.abspath (__file__)
folder_basic   = os.path.dirname (scriptPath)
Tamplates      = folder_basic + "\\" + "Tamplates"
GDB_file       = folder_basic + "\\" + "Temp"

for DWG in DWGS:
    print_arcpy_message (DWG,1)
    DWG_name       = os.path.basename(DWG).split(".")[0]
    fgdb_name      = Create_GDB      (GDB_file,DWG_name)
    csv_name       = GDB_file  + '\\' + DWG_name +'.csv'
    mxd_path       = Tamplates + '\\' + 'M1200_M1300.mxd'
    gdb_path       = Tamplates + '\\' + 'temp.gdb'
    dwg_path       = GDB_file  + '\\' + DWG_name + '.dwg'

    # # #   Get M1200 and M1300 to a layer   # # #
    Polyline                = DWG + '\\' + 'Polyline'
    Filter                  = "\"Layer\" IN('M1200','M1300')"
    layer_name              = 'Line_M1200_M1300'
    layers_M1200_M1300      = Extract_dwg_to_layer   (fgdb_name,Polyline,layer_name,Filter)


    # # #   Get all blocks and declaration   # # #
    Point                = DWG +'\\' + 'Point'
    layer_name2          = 'Blocks'
    layers_Block         = Extract_dwg_to_layer   (fgdb_name,Point,layer_name2)

    declaration = fgdb_name + '\\' + 'declaration'
    arcpy.Select_analysis (layers_Block,declaration,"\"Layer\" in ('declaration','DECLARATION','Declaration')")


    # # #   Get polygon M1200 and M1300, if not found, Create from Line   # # #
    polygon              = DWG +'\\' + 'Polygon'
    Filter3              = "\"Layer\" IN('M1200','M1300')"
    layer_name3          = "Poly_M1200_M1300"
    layers_Poly          = fgdb_name + '\\' + layer_name3
    try:
        arcpy.FeatureClassToFeatureClass_conversion( polygon, fgdb_name, layer_name3, Filter3)
        print ('Create FeatureClassToFeatureClass_conversion')
    except:
        print ('didnt Create FeatureClassToFeatureClass_conversion, trying creating polygon from line')
        # Create Polygon M1200
        poly_M1200   = 'in_memory' + '\\' + 'poly_M1200'
        Create_Polygon_From_Line         (layers_M1200_M1300 ,poly_M1200 ,"\"Layer\" = 'M1200'","'M1200'")
        Create_Polygon_From_Line         (layers_M1200_M1300,layers_Poly ,"\"Layer\" = 'M1300'","'M1300'")
        # Combine Polygons
        arcpy.Append_management          (poly_M1200,layers_Poly, "NO_TEST")

    # # #   Reading Files   # # #

    blocks   = Layer_Engine (layers_Block       ,'all')
    delcar   = Layer_Engine (declaration        ,'all')
    lines_M  = Layer_Engine (layers_M1200_M1300 ,["Layer","Entity","LyrHandle"])
    poly_M   = Layer_Engine (layers_Poly ,'all')

    blocks.Extract_shape   ()
    delcar.Extract_shape   ()
    lines_M.Extract_shape  ()

    # # #  Action  # # #

    cheak_version  = cheak_cad_version (DWG)
    Check_decler   = cheak_declaration (delcar,lines_M)
    check_Blocks   = Check_Blocks      (blocks,Point,lines_M)
    check_Lines    = Check_Lines       (lines_M)

    check_CADtoGeo   = Cheak_CADtoGeoDataBase(DWG,fgdb_name)
    check_annotation = get_crazy_long_test (DWG)

    data_csv = cheak_version + Check_decler + check_Blocks + check_Lines + check_CADtoGeo + check_annotation

    Create_CSV      (data_csv,csv_name)
    mxd_pdf_making  (mxd_path,gdb_path,DWG_name,fgdb_name,GDB_file)

print_arcpy_message('#  #  #  #  #     F I N I S H     #  #  #  #  #')





