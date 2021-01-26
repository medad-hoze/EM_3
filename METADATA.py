# -*- coding: utf-8 -*-

import pandas as pd
import json
import arcpy,os
import numpy as np


class Layer_Engine():

    def __init__(self,layer,columns = 'all'):

        if columns == 'all':
            columns = [f.name.encode('UTF-8') for f in arcpy.ListFields(layer)]
            columns.extend(['SHAPE@AREA'])
            columns.extend([b"SHAPE@WKT"])

        self.desc            = arcpy.Describe(layer)
        self.shapetype       = ShapeType(self.desc)
        self.data            = [row[:] for row in arcpy.da.SearchCursor (layer,columns)]
        self.df              = pd.DataFrame(data = self.data, columns = columns)
        self.df["geom_type"] = self.shapetype


def ShapeType(desc):
    
    if str(desc.shapeType) == 'Point':
        Geom_type = 'POINT'
    elif str(desc.shapeType) == 'Polyline':
        Geom_type = 'POLYLINE'
    else:
        Geom_type = 'POLYGON'
    return Geom_type

def add_json_endwith(json_path):
    if not os.path.basename(json_path).endswith('.json'):
        return json_path + '.json'
    else:
        return json_path

def Get_DWG_data(DWG_path,json_all):

    json_all = add_json_endwith(json_all)

    GDB_name = os.path.basename(DWG_path).split('.')[0]

    poly_path    = DWG_path + "\\" + "Polygon"
    line_path    = DWG_path + "\\" + "Polyline"
    point_path   = DWG_path + "\\" + "Point"

    layer_poly  = Layer_Engine(poly_path)
    layer_line  = Layer_Engine(line_path)
    layer_point = Layer_Engine(point_path)

    df       = pd.concat([layer_poly.df,layer_line.df,layer_point.df])
    df_group = df.groupby([b'Layer','geom_type']).size()

    df.reset_index(inplace=True)
    df.to_json (json_all)

    return df_group


# dwg_path   = r"C:\Users\Administrator\Desktop\medad\python\Work\Engine_Cad_To_Gis\DWG\TOPO-2407-113.dwg"
# json_out   = r'C:\Users\Administrator\Desktop\medad\python\Work\Engine_Cad_To_Gis\json_all'

dwg_path  = arcpy.GetParameterAsText(0) # input  - CAD
json_out  = arcpy.GetParameterAsText(1) # output - Path for json

dict1 = Get_DWG_data(dwg_path,json_out)

print (dict1)