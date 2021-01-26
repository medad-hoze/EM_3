# -*- coding: utf-8 -*-

import arcpy
import pandas as pd
import uuid,json,datetime,sys,csv,os,math
import numpy as np
from scipy.spatial import distance_matrix
from platform import python_version
import logging

class Layer_Engine():

    def __init__(self,layer,columns = 'all'):

        if columns == 'all':
            columns = [str(f.name.encode('UTF-8')) for f in arcpy.ListFields(layer)]
            columns.extend(['SHAPE@AREA'])
            columns.extend(['SHAPE@WKT'])

        self.layer           = layer
        self.gdb             = os.path.dirname  (layer)
        self.name            = os.path.basename (layer)
        self.desc            = arcpy.Describe(layer)
        self.shapetype       = ShapeType(self.desc)
        self.oid             = str(self.desc.OIDFieldName)
        self.len_columns     = len(columns)
        self.data            = [row[:] for row in arcpy.da.SearchCursor (self.layer,columns)]
        self.df              = pd.DataFrame(data = self.data, columns = columns)
        self.df["geom_type"] = self.shapetype
        self.len_rows        = self.df.shape[0]
        self.columns         = columns


def print_arcpy_message(msg,status = 1):
    '''
    return a message :
    
    print_arcpy_message('sample ... text',status = 1)
    [info][08:59] sample...text
    '''
    msg = str(msg)
    
    if status == 1:
        prefix = '[info]'
        msg = prefix + str(datetime.datetime.now()) +"  "+ msg
        # print (msg)
        arcpy.AddMessage(msg)
        
    if status == 2 :
        prefix = '[!warning!]'
        msg = prefix + str(datetime.datetime.now()) +"  "+ msg
        print (msg)
        arcpy.AddWarning(msg)
            
    if status == 0 :
        prefix = '[!!!err!!!]'
        
        msg = prefix + str(datetime.datetime.now()) +"  "+ msg
        print (msg)
        arcpy.AddWarning(msg)
        msg = prefix + str(datetime.datetime.now()) +"  "+ msg
        print (msg)
        arcpy.AddWarning(msg)
            
        warning = arcpy.GetMessages(1)
        error   = arcpy.GetMessages(2)
        arcpy.AddWarning(warning)
        arcpy.AddWarning(error)
            
    if status == 3 :
        prefix = '[!FINISH!]'
        msg = prefix + str(datetime.datetime.now()) + " " + msg
        print (msg)
        arcpy.AddWarning(msg) 

def add_field(fc,field,Type = 'TEXT'):

    TYPE = [i.name for i in arcpy.ListFields(fc) if i.name == field]
    if not TYPE:
        arcpy.AddField_management (fc, field, Type, "", "", 500)

def ShapeType(desc):
    
    if str(desc.shapeType) == 'Point':
        Geom_type = 'POINT'
    elif str(desc.shapeType) == 'Polyline':
        Geom_type = 'POLYLINE'
    else:
        Geom_type = 'POLYGON'
    return Geom_type

def uniq_fields_in_FDs_to_List(DFs_list,fields_list):

    df_conc  = pd.concat(DFs_list)
    df_conc  = df_conc[fields_list].values.tolist()
    uniq_FCs = list(set(tuple(row) for row in df_conc))

    return uniq_FCs

def data_to_dfs(data_input):
    
    if data_input.endswith('.json'):
        layer_df    = pd.read_json(data_input)
        layer_poly  = layer_df[layer_df['geom_type'] == 'POLYGON'].reset_index()
        layer_line  = layer_df[layer_df['geom_type'] == 'POLYLINE'].reset_index()
        layer_point = layer_df[layer_df['geom_type'] == 'POINT'].reset_index()
    elif data_input.endswith('.dwg'):
        layer_poly  = Layer_Engine(data_input + "\\" + "Polygon")
        layer_line  = Layer_Engine(data_input + "\\" + "Polyline")
        layer_point = Layer_Engine(data_input + "\\" + "Point")
    else:
        print_arcpy_message("Tool Can get only DWG or Json as Input")
        logger.exception("Tool Can get only DWG or Json as Input")

    return layer_poly,layer_line,layer_point

def read_excel_sheets(path2):
    # combine sheets to dataframe
    x1 = pd.ExcelFile(path2)
    df = pd.DataFrame()
    columns = None
    for idx,name in enumerate(x1.sheet_names):
        try:
            sheet = x1.parse(name)
            if idx == 0:
                columns = sheet.columns
            sheet.columns = columns
        except:
            print ("coudent read sheet {}".format(name))
        df = df.append(sheet,ignore_index = True)
            
    return df

def join_and_query_dfs(layer_,df_xlsx):

    if not isinstance(layer_, pd.DataFrame):
        layer_ = layer_.df

    layer_ = layer_.rename({"b'Layer'": 'Layer', "b'RefName'": 'RefName',"b'Entity'":'Entity',"b'SHAPE@WKT'":'SHAPE@WKT'}, axis='columns')
    layer_['index1'] = layer_.index
    # new field where BLOCK is POINT
    df_xlsx['Geom_Type'] = np.where(df_xlsx['GEOMETRY'] == 'BLOCK','POINT',df_xlsx['GEOMETRY'])
    # join xlsx and df on layer name
    result               = layer_.merge(df_xlsx,how='inner',left_on= ['Layer','geom_type'], right_on = ['LAYER','Geom_Type'])
    # query to get the right layer from 
    if layer_['geom_type'][0] == 'POINT':
        result               = result[(result["Entity"]  ==  'Insert') & ((result["BLOCK_NAME"] == result["RefName"]) | (result["BLOCK_NAME"].isnull())) & (result['Geom_Type'] == result["geom_type"])]
    else:
        result               = result[((result["BLOCK_NAME"] == result["RefName"]) | (result["BLOCK_NAME"].isnull())) & (result['Geom_Type'] == result["geom_type"])]


    result_error = layer_.loc[~layer_['index1'].isin(result['index1'])]
    result_error  = result_error.merge(df_xlsx,how='left',left_on= ['Layer','geom_type'], right_on = ['LAYER','Geom_Type'])

    result       = result      [["BLOCK_NAME","RefName","Layer","Geom_Type","geom_type","FC","LAYER.1","BLOCK_NAME.1","SHAPE@WKT"]]
    result_error = result_error[["BLOCK_NAME","RefName","Layer","Geom_Type","geom_type","FC","LAYER.1","BLOCK_NAME.1","SHAPE@WKT"]]
     
    dict_        = result.T.to_dict      ('list')
    dict_error   = result_error.T.to_dict ('list')

    return dict_,result,dict_error,result_error

def Create_GDB(GDB_file,GDB_name):
    fgdb_name = GDB_file + "\\" + GDB_name + ".gdb"
    if os.path.exists(fgdb_name):
        GDB_name = GDB_name + "_"

    fgdb_name = str(arcpy.CreateFileGDB_management(GDB_file, GDB_name, "CURRENT"))
    return fgdb_name


def Insert_dict_to_layers(dict_,gdb):
    arcpy.env.workspace = gdb
    layers              = arcpy.ListFeatureClasses()
    for i in layers:
        desc          = arcpy.Describe(i)
        shapetype     = ShapeType(desc)
        fields        = ["BLOCK_NAME","RefName","layer","data_type","SHAPE@WKT"]
        insert        = arcpy.da.InsertCursor(i,fields)

        insertion     = [insert.insertRow  ([str(value[0]),str(value[1]),str(value[2]),str(value[3]),value[8]])\
                        for key,value in dict_.items() if str(i) == str(value[5]) if shapetype == str(value[3])]

def Insert_dict_error_to_layers(dict_,gdb,Type):

    i          = arcpy.CreateFeatureclass_management(gdb,Type,Type)
    desc       = arcpy.Describe(i)
    shapetype  = ShapeType(desc)
    fields     = ['data_type_layer','data_type_xslx','BLOCK_NAME','RefName','layer','FC','SHAPE@WKT']
    add_Fields = [add_field(i,f) for f in fields if f != 'SHAPE@WKT']

    insert    = arcpy.da.InsertCursor(i,fields)
    insertion = [insert.insertRow  ([str(value[4]),str(value[3]),str(value[0]),str(value[1]),str(value[2]),str(value[5]),value[-1]])\
                for key,value in dict_.items() if shapetype == str(value[4])]


def create_layers(gdb,list_fc_type):
    arcpy.env.workspace = gdb
    temp_layer = "in_memory" + '\\' + "template"
    arcpy.CreateFeatureclass_management("in_memory","template","POINT")
    add_Fields = [add_field(temp_layer,i) for i in ['data_type','BLOCK_NAME','RefName','layer']]
    exe = [arcpy.CreateFeatureclass_management(gdb,str(value[0]),value[1],temp_layer) for value in list_fc_type]

def Get_Time():
    now = datetime.datetime.now()
    return 'Time_' + str(now.hour) +'_'+ str(now.minute) + '_' + str(now.second)

def add_endwith(json_path,endswith_):
    if not os.path.basename(json_path).endswith(endswith_):
        return json_path + endswith_

def Create_Pdfs(mxd_path,gdb_Tamplate,gdb_path,pdf_output):

    pdf_output = add_endwith(pdf_output,endswith_ = '.pdf')

    p = arcpy.mp.ArcGISProject (mxd_path)
    p.updateConnectionProperties(gdb_Tamplate, gdb_path)

    # get 1 of the layers for zoom in
    m = p.listMaps('Map')[0]
    lyr = m.listLayers()[1]

    delete_templates = [m.removeLayer(i) for i in m.listLayers() if ('Tamplates' in i.dataSource)]

    lyt = p.listLayouts    ("Layout1")[0]
    mf  = lyt.listElements ('MAPFRAME_ELEMENT',"Map Frame")[0]
    mf.camera.setExtent    (mf.getLayerExtent(lyr,False,True))

    mf.exportToPDF(pdf_output)

# # #  Main  # # #

# data_file   = r"C:\Users\Administrator\Desktop\medad\python\Work\Engine_Cad_To_Gis\Json_try.json"
# input_data  = r'C:\GIS_layers\Vector\bad_DWG\json_all_.json'


input_data        = arcpy.GetParameterAsText(0) # input   - json or dwg   , Data
data_file         = arcpy.GetParameterAsText(1) # input   - json or excel , Referance

# Templates
mxd_path       = r"C:\Users\Administrator\Desktop\medad\python\Work\Engine_Cad_To_Gis\Tamplates\CONVERTOR.aprx"
gdb_path_error = r"C:\Users\Administrator\Desktop\medad\python\Work\Engine_Cad_To_Gis\Tamplates\CONV_Error.gdb"
gdb_Tamplate   = r""

print_arcpy_message(" #      #      #       S T A R T       #      #      #",status = 1)

scriptPath     = os.path.abspath (__file__)

GDB_file       = os.path.dirname (scriptPath)
GDB_name       = Get_Time()
GDB_name_error = Get_Time() + '_Error'


logger = logging.getLogger(__name__)

formatter    = logging.Formatter('%(asctime)s:%(name)s:%(message)s')

file_handler = logging.FileHandler(GDB_file + '\\'+'CONVERTER.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.ERROR)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)


print_arcpy_message(" # # #  import data (json\DWG)   # # #",status = 1)

layer_poly,layer_line,layer_point = data_to_dfs(input_data)

print_arcpy_message(" # # #   read_excel_or_json_sheets   # # #",status = 1)

if data_file.endswith('.xlsx'):
    df_xlsx  = read_excel_sheets(data_file)
elif data_file.endswith('.json'):
    df_xlsx  = pd.read_json(data_file)
else:
    print_arcpy_message("reading data from Xlsx and json only")

print_arcpy_message(" # # #   Merge_and_query_dfs   # # #",status = 1)

dict_poly  ,df_filter_poly  ,dict_poly_error,  Error_poly   = join_and_query_dfs(layer_poly,df_xlsx )
dict_line  ,df_filter_line  ,dict_line_error,  Error_line   = join_and_query_dfs(layer_line,df_xlsx )
dict_point ,df_filter_point ,dict_point_error, Error_point  = join_and_query_dfs(layer_point,df_xlsx)


print_arcpy_message(" # # #   Create_GDB   # # #",status = 1)
logger.debug(" # # #   Create_GDB   # # #")

gdb       = Create_GDB(GDB_file,GDB_name)
gdb_error = Create_GDB(GDB_file,GDB_name_error)

print_arcpy_message(" # # #   Insert_erros_dict_to_layers   # # #",status = 1)
logger.debug(" # # #   Insert_erros_dict_to_layers   # # #")

Insert_dict_error_to_layers(dict_poly_error,gdb_error  ,'POLYGON')
Insert_dict_error_to_layers(dict_line_error,gdb_error  ,'POLYLINE')  
Insert_dict_error_to_layers(dict_point_error,gdb_error ,'POINT')

print_arcpy_message(" # # #   create_layers   # # #",status = 1)
logger.debug(" # # #   create_layers   # # #")

uniq_FCs    = uniq_fields_in_FDs_to_List ([df_filter_poly,df_filter_line,df_filter_point],["FC","Geom_Type"])

create_layers(gdb,uniq_FCs)

print_arcpy_message(" # # #   Insert_dict_to_layers   # # #",status = 1)
logger.debug(" # # #   Insert_dict_to_layers   # # #")

Insert_dict_to_layers(dict_poly,gdb)
Insert_dict_to_layers(dict_line,gdb)
Insert_dict_to_layers(dict_point,gdb)

print_arcpy_message(" # # #   Create PDFs   # # #",status = 1)
# Create_Pdfs(mxd_path,gdb_Tamplate,gdb,pdf_output)
Create_Pdfs(mxd_path,gdb_path_error,gdb_error,GDB_file +"\\"+ GDB_name_error)

print_arcpy_message(" #      #      #       F I N S H       #      #      #",status = 1)

