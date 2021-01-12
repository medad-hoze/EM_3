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

GDB_name = os.path.basename(path).split('.')[0]

poly_path    = path + "\\" + "Polygon"
line_path    = path + "\\" + "Polyline"
point_path   = path + "\\" + "Point"

print_arcpy_message(" # # #   Layer_Engine   # # #",status = 1)

layer_poly  = Layer_Engine(poly_path)
layer_line  = Layer_Engine(line_path)
layer_point = Layer_Engine(point_path)

print_arcpy_message(" # # #   read_excel_sheets   # # #",status = 1)

df_xlsx  = read_excel_sheets(xlsx)

print_arcpy_message(" # # #   join_and_query_dfs   # # #",status = 1)

dict_poly  ,df_filter_poly   = join_and_query_dfs(layer_poly,df_xlsx)
dict_line  ,df_filter_line   = join_and_query_dfs(layer_line,df_xlsx)
dict_point ,df_filter_point  = join_and_query_dfs(layer_point,df_xlsx)


print_arcpy_message(" # # #   Create_GDB   # # #",status = 1)

gdb = Create_GDB(GDB_file,GDB_name)

print_arcpy_message(" # # #   create_layers   # # #",status = 1)

df_conc  = pd.concat([df_filter_poly,df_filter_line,df_filter_point])
df_conc  = df_conc[["FC","Geom_Type"]].values.tolist()
uniq_FCs = list(set(tuple(row) for row in df_conc))

create_layers(gdb,uniq_FCs)

print_arcpy_message(" # # #   Insert_dict_to_layers   # # #",status = 1)

Insert_dict_to_layers(dict_poly,gdb)
Insert_dict_to_layers(dict_line,gdb)
Insert_dict_to_layers(dict_point,gdb)

print_arcpy_message(" #      #      #       F I N S H       #      #      #",status = 1)