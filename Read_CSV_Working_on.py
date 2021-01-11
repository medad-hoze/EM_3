# -*- coding: utf-8 -*-

import pandas as pd
import json
import arcpy,os
import numpy as np

from Engine_class import Layer_Engine
from Basic_Tools  import *


xlsx = r"C:\Users\medad\python\GIStools\Work Tools\Engine_Cad_To_Gis\DATA_DIC_20200218-MAVAAT.xlsx"

# path = r"C:\GIS_layers\Vector\bad_DWG\15_11_2019\Migrash_528_2.dwg"
path = r"C:\GIS_layers\Vector\bad_DWG\19_11_2019\TOPO-2407-113.dwg"

GDB_file = r'C:\GIS_layers'


print_arcpy_message(" #      #      #       S T A R T       #      #      #",status = 1)

GDB_name = os.path.basename(path).split('.')[0]

poly_path    = path + "\\" + "Polygon"
line_path    = path + "\\" + "Polyline"
point_path   = path + "\\" + "Point"

print_arcpy_message(" # # #   Layer_Engine   # # #",status = 1)

layer_poly  = Layer_Engine(poly_path)
layer_line  = Layer_Engine(line_path)
layer_point = Layer_Engine(point_path)

print_arcpy_message(" # # #   read_excel_sheets   # # #",status = 1)

read_excel  = read_excel_sheets(xlsx)

df_xlsx     = read_excel.set_index('LAYER')

print_arcpy_message(" # # #   join_and_query_dfs   # # #",status = 1)

dict_poly   = join_and_query_dfs(layer_poly,df_xlsx)
dict_line   = join_and_query_dfs(layer_line,df_xlsx)
dict_point  = join_and_query_dfs(layer_point,df_xlsx)

# # # Get attri of all layers and connect to layers # # #

# df_attri    =  read_excel[~read_excel['LAYER.1'].isnull()]
# df_attri    = df_attri.set_index('LAYER.1')
# dict_attri  = Get_Attri_blocks_to_dict(df_attri,layer_point)
# Connect_attri_layer(dict_attri,dict_poly)

print_arcpy_message(" # # #   Create_GDB   # # #",status = 1)

gdb = Create_GDB(GDB_file,GDB_name)

print_arcpy_message(" # # #   create_layers   # # #",status = 1)

create_layers(gdb,dict_poly)

print_arcpy_message(" # # #   Insert_dict_to_layers   # # #",status = 1)

Insert_dict_to_layers(dict_poly,gdb)
Insert_dict_to_layers(dict_line,gdb)
Insert_dict_to_layers(dict_point,gdb)

print_arcpy_message(" #      #      #       F I N S H       #      #      #",status = 1)