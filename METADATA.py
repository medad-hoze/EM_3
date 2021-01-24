# -*- coding: utf-8 -*-

import pandas as pd
import json
import arcpy,os
import numpy as np


class Layer_Engine():

    def __init__(self,layer,columns = 'all'):

        if columns == 'all':
            columns = [str(f.name.encode('UTF-8')) for f in arcpy.ListFields(layer)]
            columns.extend(['SHAPE@AREA'])
            columns.extend(["SHAPE@WKT"])

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


def Get_DWG_data(DWG_path,json_folder):

    GDB_name = os.path.basename(DWG_path).split('.')[0]

    poly_path    = DWG_path + "\\" + "Polygon"
    line_path    = DWG_path + "\\" + "Polyline"
    point_path   = DWG_path + "\\" + "Point"

    json_poly  = json_folder + '\\' + 'Polygon.json'
    json_line  = json_folder + '\\' + 'Polyline.json'
    json_point = json_folder + '\\' + 'Point.json'

    layer_poly  = Layer_Engine(poly_path)
    layer_line  = Layer_Engine(line_path)
    layer_point = Layer_Engine(point_path)

    df       = pd.concat([layer_poly.df,layer_line.df,layer_point.df])
    df_group = df.groupby(['Layer','geom_type']).size()


    json_all = json_folder + '\\' + 'json_all_.json'
    df.reset_index(inplace=True)
    json_    = df.to_json (json_all)

    return df_group


dwg_path    = r"C:\GIS_layers\Vector\bad_DWG\19_11_2019\TOPO-2407-113.dwg"
csv_out_put = r'C:\Users\medad\python\GIStools\Work Tools\Engine_Cad_To_Gis'

dict1 = Get_DWG_data(dwg_path,csv_out_put)

print (dict1)