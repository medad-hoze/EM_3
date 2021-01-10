# -*- coding: utf-8 -*-

import pandas as pd
import json
import arcpy,os

from Engine_class import Layer_Engine

def ShapeType(desc):
    
    if str(desc.shapeType) == 'Point':
        Geom_type = 'Point'
    elif str(desc.shapeType) == 'Polyline':
        Geom_type = 'Polyline'
    else:
        Geom_type = 'Polygon'
    return Geom_type


def Connect_rows(x,y):
    return str(x) + '-' + str(y)



csv_ = r"C:\Users\medad\python\GIStools\Work Tools\Engine_Cad_To_Gis\LUT 03112020.csv"
path = r"C:\GIS_layers\Vector\bad_DWG\15_11_2019\Migrash_528_2.dwg"

poly_path    = path + "\\" + "Polygon"
line_path    = path + "\\" + "Polyline"
point_path   = path + "\\" + "Point"

layer_search = "M1200"

layer_poly  = Layer_Engine(poly_path)
layer_line  = Layer_Engine(line_path)
layer_point = Layer_Engine(point_path)

poly_uni    = layer_poly.df["Layer"].unique()

layers        = [layer_poly,layer_line,layer_point]
layers_Filter = []

for layer in layers:
    df_layer = layer.Get_Field_Count_to_df("Layer")
    df_layer = df_layer[df_layer['Layer'] == layer_search]
    layers_Filter.append(df_layer)

All_df = pd.concat(layers_Filter, ignore_index=True)
print (All_df["Layer_num"])

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

