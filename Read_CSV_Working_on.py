# -*- coding: utf-8 -*-

import pandas as pd
import json
import arcpy,os
import numpy as np

from Engine_class import Layer_Engine
from Basic_Tools  import *


xlsx = r"C:\Users\medad\python\GIStools\Work Tools\Engine_Cad_To_Gis\DATA_DIC_20200218-MAVAAT.xlsx"
path = r"C:\GIS_layers\Vector\bad_DWG\15_11_2019\Migrash_528_2.dwg"

GDB_file = r'C:\GIS_layers'
GDB_name = os.path.basename(path).split('.')[0]

poly_path    = path + "\\" + "Polygon"
line_path    = path + "\\" + "Polyline"
point_path   = path + "\\" + "Point"

layer_search = "M1200"

layer_poly  = Layer_Engine(poly_path)
layer_line  = Layer_Engine(line_path)
layer_point = Layer_Engine(point_path)

df_xlsx     = read_excel_sheets(xlsx).set_index('LAYER')

dict_poly   = join_and_query_dfs(layer_poly,df_xlsx)
dict_line   = join_and_query_dfs(layer_line,df_xlsx)
dict_point  = join_and_query_dfs(layer_point,df_xlsx)

print (dict_point)

gdb = Create_GDB(GDB_file,GDB_name)

create_layers(gdb,dict_poly)
create_layers(gdb,dict_line)
create_layers(gdb,dict_point)




# result.to_csv(r'C:\Users\medad\python\GIStools\Work Tools\Engine_Cad_To_Gis\excel.csv',encoding='utf-8')


# .agg({'Layer', lambda x: list(x)}))

# print (layer_1.df.groupby('Layer').len_rows)
# .agg({'Entity', list})
# print (layer_1.df.groupby(['Layer']).Entity.unique().reset_index())
# .agg({'qty': [('std_qty','std'), ('mean_qty','mean')]})

# df      = pd.read_csv(csv_)

# cols = df.columns.difference(['Col1'])

# print (cols)

# result = df.to_json(orient="index")
# parsed = json.loads(result)
# print (parsed["216"]["OWNER"])

