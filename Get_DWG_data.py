# -*- coding: utf-8 -*-

import pandas as pd
import json
import arcpy,os
import numpy as np

from Engine_class import Layer_Engine
from Basic_Tools  import *



path       = r"C:\GIS_layers\Vector\bad_DWG\19_11_2019\TOPO-2407-113.dwg"

folder_csv = r"C:\GIS_layers"



GDB_name = os.path.basename(path).split('.')[0]

poly_path    = path + "\\" + "Polygon"
line_path    = path + "\\" + "Polyline"
point_path   = path + "\\" + "Point"

layer_poly  = Layer_Engine(poly_path)
layer_line  = Layer_Engine(line_path)
layer_point = Layer_Engine(point_path)

layer_poly.Groupby_and_count('Layer')
layer_line.Groupby_and_count('Layer')
layer_point.Groupby_and_count('Layer')


poly_dict  = layer_poly.Dict('Layer')
line_dict  = layer_line.Dict('Layer')
point_dict = layer_point.Dict('Layer')


layer_poly.create_csv(folder_csv)
layer_line.create_csv(folder_csv)
layer_point.create_csv(folder_csv)

print (poly_dict)
print (line_dict)
print (point_dict)

