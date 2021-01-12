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
# path = r'C:\GIS_layers\Vector\bad_DWG\16_9_2019\100239-28-040819(1561).dwg'

GDB_file = r'C:\GIS_layers'


print_arcpy_message(" #      #      #       S T A R T       #      #      #",status = 1)

GDB_name       = os.path.basename(path).split('.')[0]
GDB_name_error = os.path.basename(path).split('.')[0] + '_Error'

poly_path    = path + "\\" + "Polygon"
line_path    = path + "\\" + "Polyline"
point_path   = path + "\\" + "Point"

print_arcpy_message(" # # #   Layer_Engine   # # #",status = 1)

layer_poly  = Layer_Engine(poly_path)
layer_line  = Layer_Engine(line_path)
layer_point = Layer_Engine(point_path)

print_arcpy_message(" # # #   read_excel_sheets   # # #",status = 1)

df_xlsx  = read_excel_sheets(xlsx)

print_arcpy_message(" # # #   Merge_and_query_dfs   # # #",status = 1)

dict_poly  ,df_filter_poly  ,dict_poly_error,  Error_poly  = join_and_query_dfs(layer_poly,df_xlsx )
dict_line  ,df_filter_line  ,dict_line_error,  Error_line   = join_and_query_dfs(layer_line,df_xlsx )
dict_point ,df_filter_point ,dict_point_error, Error_point  = join_and_query_dfs(layer_point,df_xlsx)


print_arcpy_message(" # # #   Create_GDB   # # #",status = 1)

gdb       = Create_GDB(GDB_file,GDB_name)
gdb_error = Create_GDB(GDB_file,GDB_name_error)

print_arcpy_message(" # # #   Insert_erros_dict_to_layers   # # #",status = 1)

Insert_dict_error_to_layers(dict_poly_error,gdb_error  ,'POLYGON')
Insert_dict_error_to_layers(dict_line_error,gdb_error  ,'POLYLINE')  
Insert_dict_error_to_layers(dict_point_error,gdb_error ,'POINT')

print_arcpy_message(" # # #   create_layers   # # #",status = 1)

uniq_FCs    = uniq_fields_in_FDs_to_List ([df_filter_poly,df_filter_line,df_filter_point],["FC","Geom_Type"])

create_layers(gdb,uniq_FCs)

print_arcpy_message(" # # #   Insert_dict_to_layers   # # #",status = 1)

Insert_dict_to_layers(dict_poly,gdb)
Insert_dict_to_layers(dict_line,gdb)
Insert_dict_to_layers(dict_point,gdb)


print_arcpy_message(" #      #      #       F I N S H       #      #      #",status = 1)


