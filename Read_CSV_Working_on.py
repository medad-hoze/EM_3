# -*- coding: utf-8 -*-

import pandas as pd
import json
import arcpy,os

from Engine_class import Layer_Engine
from Basic_Tools  import *


xlsx = r"C:\Users\medad\python\GIStools\Work Tools\Engine_Cad_To_Gis\DATA_DIC_20200218-MAVAAT.xlsx"
path = r"C:\GIS_layers\Vector\bad_DWG\15_11_2019\Migrash_528_2.dwg"

poly_path    = path + "\\" + "Polygon"
line_path    = path + "\\" + "Polyline"
point_path   = path + "\\" + "Point"

layer_search = "M1200"

layer_poly  = Layer_Engine(poly_path)
layer_line  = Layer_Engine(line_path)
layer_point = Layer_Engine(point_path)

layers        = [layer_poly.df,layer_line.df,layer_point.df]

All_df  = pd.concat(layers, ignore_index=True).set_index('Layer')


df_xlsx = read_excel_sheets(xlsx).set_index('LAYER')

result  = All_df.join(df_xlsx,how='inner')

a = result

a.to_csv(r'C:\Users\medad\python\GIStools\Work Tools\Engine_Cad_To_Gis\excel.csv',encoding='utf-8')
print (a)

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

