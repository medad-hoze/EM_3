
# -*- coding: utf-8 -*-

import arcpy
import pandas as pd
import uuid,json,datetime,sys,csv,os,math
import numpy as np
from scipy.spatial import distance_matrix
from platform import python_version

arcpy.env.overwriteOutPut = True


'''
print_arcpy_message
createFolder
Extract_dwg_to_layer
Create_GDB
ShapeType
'''


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


def createFolder(dic):
	try:
		if not os.path.exists(dic):
			os.makedirs(dic)
	except OSError:
		print ("Error Create dic")


def Extract_dwg_to_layer(fgdb_name,DWF_layer,layer_name,Filter = ''):
    try:
        fc_out_line   = str(arcpy.FeatureClassToFeatureClass_conversion( DWF_layer, fgdb_name, layer_name, Filter))
        return fc_out_line
    except:
        msg = r"Coudnt Make FeatureClassToFeatureClass_conversion for layers M1200 and M1300"
        print_arcpy_message(msg,2)
        

def Create_GDB(GDB_file,GDB_name):
    fgdb_name = GDB_file + "\\" + GDB_name + ".gdb"
    if os.path.exists(fgdb_name):
        GDB_name = GDB_name + "_"
    fgdb_name = str(arcpy.CreateFileGDB_management(GDB_file, str(GDB_name), "CURRENT"))
    return fgdb_name


def ShapeType(desc):
    
    if str(desc.shapeType) == 'Point':
        Geom_type = 'POINT'
    elif str(desc.shapeType) == 'Polyline':
        Geom_type = 'POLYLINE'
    else:
        Geom_type = 'POLYGON'
    return Geom_type


def Connect_rows(x,y):
    return str(x) + '-' + str(y)


def cheak_cad_version(DWG):
    
	dictme={'AC1014':'AutoCAD Release 14','AC1015': 'AutoCAD2000','AC1018': 'AutoCAD2004','AC1021': 'AutoCAD2007','AC1024': 'AutoCAD2010','AC1027': 'AutoCAD2013','AC1032': 'AutoCAD2018'}
	if (str(python_version())) == '2.7.16': # Arcmap
		x = open(DWG,'r').read(6)
	else:
		file1 = open(DWG,errors='ignore')
		x     = file1.readline()[:6]
	cheak_version = []
	try:
		cheak_version = [i for n,i in dictme.items() if x == n]
	except:
		print_arcpy_message  ("coudent exctract DWG version",status = 2)
		cheak_version.append ("coudent exctract DWG version")
	
	bad_ver = ['AutoCAD2000','AutoCAD2013','AutoCAD2018','AutoCAD Release 14']
	
	if cheak_version[0] in bad_ver:
		print_arcpy_message  ("the CAD version is {}, and is not supported".format(cheak_version[0]),status = 2)
		cheak_version.append ("the CAD version is {}, and is not supported".format(cheak_version[0]))
	else:
		print_arcpy_message("the CAD version is {}".format(cheak_version[0]),status = 1)

	return cheak_version


def Create_Polygon_From_Line(polyline,Out_put,fillter,field_name):
    arcpy.CopyFeatures_management(arcpy.Polygon(arcpy.Array([arcpy.Point(j.X,j.Y) for i in arcpy.SearchCursor (polyline,fillter) for n in i.shape for j in n if j])),Out_put)
    arcpy.AddField_management        (Out_put,'Layer','TEXT')
    arcpy.CalculateField_management  (Out_put,"Layer", field_name, "PYTHON_9.3")

    return Out_put


def Dis_2arrays_max(pts_1,pts_2,Max_num = 10000,After_zero = 2):
    
    '''
    [INFO]
        Find the longest points from array1 to array2as [id,pt1,pt2,dis]
    input: 
        pts_1 = [[1,2],[2,3]]
        pts_2 = [[3,5],[4,6]]
    out_put:
        array_dis = [['1-2',[1, 2], [4, 6],5.0]
                     ['2-3'[2, 3], [3, 5]],3.6]
    
    '''
    dis_array  = distance_matrix(pts_1,pts_2)
    
    if pts_1 == pts_2:
        np.fill_diagonal(dis_array,np.inf)

    closest_points = dis_array.argmax(axis = 1)
    
    new_list = [[str(round(pts_1[i][0],After_zero)) + '-' + str(round(pts_1[i][1],After_zero))\
                    ,pts_1[i],pts_2[closest_points[i]],round(dis_array[i,closest_points[i]],After_zero)]\
                for i in range(len(pts_1)) if dis_array[i,closest_points[i]] > Max_num]


    return new_list


def dis(x1,x2,y1,y2):
    return math.sqrt(((x1-x2)**2) + ((y1-y2)**2))


def Check_distance_data_shape(point,line):
    x1,y1  = [point[0][4] , point[0][5]]
    x2,y2  = [line [0][1] , line [0][2]]
    return dis(x1,x2,y1,y2)



def cheak_declaration(obj_declar,obj_line):

    declaration = []

    # check if there is declaration in file
    if obj_declar.len_rows == 0:
        print_arcpy_message ("No Declaration Found",2)
        declaration.append  ("No Declaration Found")
    elif obj_declar.len_rows > 1:
        print_arcpy_message ("you have {} declarations, only 1 is approved".format(obj_declar.len_rows),2)
        declaration.append  ("you have {} declarations, only 1 is approved".format(obj_declar.len_rows))

    # check if distance to line is bigger then 100,000 meters
    distance = Check_distance_data_shape(obj_declar.data_shape,obj_line.data_shape)
    if distance > 100000:
        print_arcpy_message ("Declaration is more then 100,000m from M1300",2)
        declaration.append  ("Declaration is more then 100,000m from M1300")

    # check if all columns in decleration (date fields)
    not_exists_fields = obj_declar.Check_Columns_names()
    if not_exists_fields:
        print_arcpy_message ("declaration missing fields: {}".format(str(not_exists_fields)),2)
        declaration.append  ("declaration missing fields: {}".format(str(not_exists_fields)))

    # check if missing values in: SURVEYOR, ACCURACY_HOR , ACCURACY_VER

    def missing_digi_in_field(df,field_name):
        declaration = []
        data = pd.to_numeric(df[field_name], errors='coerce').notnull().all()
        if not data:
            print_arcpy_message('field {} have no Value'.format(field_name),status = 2)
            declaration.append(field_name + '  no value inside')
        return declaration

    declaration = missing_digi_in_field(obj_declar.df,'SURVEYOR')
    declaration = missing_digi_in_field(obj_declar.df,'ACCURACY_VER')
    declaration = missing_digi_in_field(obj_declar.df,'ACCURACY_HOR')

        
    # check if date is correct !!! why not extract from df??

    obj_declar.Filter_df('Entity','Insert',True)
    list_fileds    = obj_declar.columns
    field_must     = ["SURVEY_YYYY","SURVEY_MM","SURVEY_DD","FINISH_YYYY","FINISH_MM","FINISH_DD"]
    missing_fields = [i for i in field_must if i not in list_fileds]
    if missing_fields == []:
        one_two = [1,2]
        if int(str(arcpy.GetCount_management(obj_declar.layer))) > 0:
                data_date = [obj_declar.Len_field(field,as_int = True) for field in field_must]
                if data_date[0] != 4:
                        print_arcpy_message("there is {} numbers in field: SURVEY_YYYY, 4 needed".format(str(data_date[0]),status = 2))
                        declaration.append("there is {} numbers in field: SURVEY_YYYY, 4 needed".format(data_date[0]))
                if data_date[1] not in one_two:
                        print_arcpy_message("there is {} numbers in field: SURVEY_MM, 2 needed".format(str(data_date[1])),status = 2)
                        declaration.append("there is {} numbers in field: SURVEY_MM, only 2 or 1 digits exepted".format(data_date[1]))
                if data_date[2] not in one_two:
                        print_arcpy_message("there is {} numbers in field: SURVEY_DD, 2 needed".format(str(data_date[2])),status = 2)
                        declaration.append("there is {} numbers in field: SURVEY_DD, only 2 or 1 digits exepted".format(data_date[2]))
                if data_date[3] != 4:
                        print_arcpy_message("there is {} numbers in field: FINISH_YYYY, 4 needed".format(str(data_date[3])),status = 2)
                        declaration.append("there is {} numbers in field: FINISH_YYYY, 4 needed".format(data_date[3]))
                if data_date[4] not in one_two:
                        print_arcpy_message("there is {} numbers in field: FINISH_MM, 2 needed".format(str(data_date[4])),status = 2)
                        declaration.append("there is {} numbers in field: FINISH_MM, , only 2 or 1 digits exepted".format(data_date[4]))
                if data_date[5] not in one_two:
                        print_arcpy_message("there is {} numbers in field: FINISH_DD, only 2 or 1 digits exepted".format(str(data_date[5])),status = 2)
                        declaration.append("there is {} numbers in field: FINISH_DD, 2 needed".format(data_date[5]))
        else:
                print_arcpy_message("layer 'declaration' have no features",status = 2)
                declaration.append("layer 'declaration' have no features")
    else:
            print_arcpy_message("layer 'declaration' missing fields: {}".format(''.join([i + '-' for i in missing_fields])[0:-1],status = 2))
            declaration.append("Missing fields")
            declaration.append(missing_fields)

    return declaration


def Check_Blocks (obj_blocks,Point,Line_object):
    
    blocks     = []
    bad_charc     = ['-','"','.']
    cach_fields = [str(i.name) for i in arcpy.ListFields(Point) for n in i.name if n in bad_charc]
    if cach_fields:
        for letter in cach_fields:
            print_arcpy_message ('you have bad letters in a field of the point layer, letter: {}'.format(letter),2)
            blocks.append       ('you have bad letters in a field of the point layer, letter: {}'.format(letter))


    # check if there is block in coordinate 0,0
    at_Zero_Zero = obj_blocks.Check_Block_0_0()
    if len(at_Zero_Zero) > 0:
        print_arcpy_message ('you have blocks at coordinates 0,0',2)
        blocks.append       ('you have blocks at coordinates 0,0')
        for i in at_Zero_Zero:
            blocks.append       ('layer: {}, have blocks at coordinates 0,0'.format(i[1]))
            print_arcpy_message('block: {}'.format(str(i)),2)


    # Check if there is points with distance then more 100,000m from point
    x_y       = [[i[1],i[2]] for i in Line_object.data_shape]
    if x_y[0]:
        far_point = obj_blocks.Filter_point_by_max_distance([x_y[0]],100000)  # enough chacking 1 vertex of line to know if block is to far
        far_point = far_point[['Layer','Entity','X_Y']][((far_point['X'] != 0.0) | (far_point['Y'] != 0.0)) & (far_point['Entity'] == 'Insert')].values.tolist()
        if len(far_point) > 0:
            print_arcpy_message ('you have blocks far from AOI',2)
            blocks.append       ('you have blocks far from AOI')
            for i in far_point:
                blocks.append       ('layer: {}, block name: {}, have coordinates at  {}'.format(i[0],i[1],i[2]))
                print_arcpy_message ('layer: {}, block name: {}, have coordinates at  {}'.format(i[0],i[1],i[2]),2)
        
    return blocks

def Check_Lines(obj_lines):

    lines = []
    close_pnt_m1300,close_pnt_m1200 = False,False

    # check if there is self intersect of vertxs
    if obj_lines.df[obj_lines.df['Layer'] == 'M1200'].values.tolist():
        close_pnt_m1200 = obj_lines.Close_vertxs('M1200',0.1)
    if obj_lines.df[obj_lines.df['Layer'] == 'M1300'].values.tolist():
        close_pnt_m1300 = obj_lines.Close_vertxs('M1300',0.1)

    if close_pnt_m1200:
        print_arcpy_message('you have self-intersect vertxs at layer M1200',2)
        lines.append       ('you have self-intersect vertxs at layer M1200')
        for i in close_pnt_m1200:
            print_arcpy_message ('M1200 vertxs = {}'.format(str(i)),2)
            lines.append        ('M1200 vertxs = {}'.format(str(i)))

    if close_pnt_m1300:
        print_arcpy_message('you have self-intersect vertxs at layer M1300',2)
        lines.append       ('you have self-intersect vertxs at layer M1300')
        for i in close_pnt_m1300:
            print_arcpy_message  ('M1300 vertxs = {}'.format(str(i)))
            lines.append         ('M1300 vertxs = {}'.format(str(i)))


    # check Curves 
    obj_lines.Curves(obj_lines.layer + '_Curves')
    if obj_lines.exists_curves:
        print_arcpy_message('You have curves in layer, plz check error layer {}'.format(obj_lines.layer + '_Curves'))
        lines.append       ('You have curves in layer, plz check error layer {}'.format(obj_lines.layer + '_Curves'))

    # check more then 1 - M1200 or M1300
    only_1_layer = True
    M1200 = obj_lines.Filter_df('Layer','M1200')
    M1300 = obj_lines.Filter_df('Layer','M1300')
    if M1200.shape[0] > 1 or M1200.shape[0] == 0:
        print_arcpy_message("you have {} M1200,  1 is expected".format(str(M1200.shape[0])),2)
        lines.append       ("you have {} M1200,  1 is expected".format(str(M1200.shape[0])))
        only_1_layer = False
    if M1300.shape[0] > 1 or M1300.shape[0] == 0:
        print_arcpy_message("you have {} M1300,  1 is expected".format(str(M1300.shape[0])),2)
        lines.append       ("you have {} M1300,  1 is expected".format(str(M1300.shape[0])))
        only_1_layer = False

    # check if line are not closed
    if only_1_layer:
        obj_lines.Shape_closed()
        if obj_lines.Not_closed:
            print_arcpy_message ('there is vertexs that are not closed',2)
            lines.append        ('there is vertexs that are not closed')
            for i in obj_lines.Not_closed:
                print_arcpy_message ('vertx that is not closed: {}'.format(i),2)
                lines.append        ('vertx that is not closed: {}'.format(i))

    return lines

def Create_CSV(data,csv_name):
    df        = pd.DataFrame(data)
    df.to_csv(csv_name)



def mxd_pdf_making(mxd_path,gdb_path,name,gdb,out_put):

        mxd = arcpy.mapping.MapDocument    (mxd_path)
        mxd.findAndReplaceWorkspacePaths   (gdb_path, gdb)

        df           = arcpy.mapping.ListDataFrames  (mxd)[0]
        BORDER_Layer = arcpy.mapping.ListLayers      (mxd, "", df)[-1]
        df.extent    = BORDER_Layer.getExtent        ()

        mxd.saveACopy     (gdb + "\\Cheack_"+name+".mxd")
        arcpy.AddMessage  ("Open MXD Copy")
        # os.startfile      (gdb + "\\Cheack_"+name+".mxd")
        
        arcpy.mapping.ExportToPDF(mxd,out_put +r"\\Report_"+name+".pdf")
        del mxd

def Cheak_CADtoGeoDataBase(DWG,fgdb_name):	
    # checking if arcpy can make layer to Geodatabase
	CADtoGeoDataBase = []
	try:
		arcpy.CADToGeodatabase_conversion(DWG,fgdb_name,'chacking',1)
		print_arcpy_message("tool made CAD to Geodatabase" , status = 1)
	except:
		print_arcpy_message("tool didnt made CAD to Geodatabase" , status = 0)
		CADtoGeoDataBase.append('tool didnt made CAD to Geodatabase')

    # check declaration in Geodatabase
	layer_cheacking = fgdb_name + '\\' + 'chacking\Point'
	decl_list = [row[0] for row in arcpy.da.SearchCursor(layer_cheacking,["Layer"]) if row[0] in ('declaration','DECLARATION')]
	if len(decl_list) > 1 or len(decl_list) == 0:
		massage = "layer declaration from chacking\point (Geodatabase) found {} declaration, must be 1 ".format(len(decl_list))
		print_arcpy_message(massage, status = 2)
		CADtoGeoDataBase.append(massage)

	return CADtoGeoDataBase

def get_crazy_long_test(DWG):
		long_prob = []
		anno  = DWG +'\\' + 'Annotation'
		x = [[row[0],row[1],row[2],row[3]] for row in arcpy.da.SearchCursor (anno,['Layer','TxtMemo','Entity','RefName'])]
		for i in x:
			if (len(i[1]) > 254) or (len(i[2]) > 254) or (len(i[3]) > 254):
				print_arcpy_message("{} is with more then 254 characters, plz notice".format(str(i[0])),status = 2)
				long_prob.append   ("{} is with more then 254 characters".format(i[0]))
				
		return long_prob

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

    if isinstance(layer_, pd.DataFrame):
        result       = result      [["BLOCK_NAME","RefName","Layer","Geom_Type","geom_type","FC","LAYER.1","BLOCK_NAME.1","SHAPE@WKT"]]
        result_error = result_error[["BLOCK_NAME","RefName","Layer","Geom_Type","geom_type","FC","LAYER.1","BLOCK_NAME.1","SHAPE@WKT"]]
    else:
        result       = result      [["BLOCK_NAME","RefName","Layer","Geom_Type","geom_type","FC","LAYER.1","BLOCK_NAME.1","SHAPE@"]]
        result_error = result_error[["BLOCK_NAME","RefName","Layer","Geom_Type","geom_type","FC","LAYER.1","BLOCK_NAME.1","SHAPE@"]]        

    dict_        = result.T.to_dict      ('list')
    dict_error   = result_error.T.to_dict ('list')

    return dict_,result,dict_error,result_error





def create_layers(gdb,list_fc_type):
    arcpy.env.workspace = gdb
    temp_layer = "in_memory" + '\\' + "template"
    arcpy.CreateFeatureclass_management("in_memory","template","POINT")
    add_Fields = [add_field(temp_layer,i) for i in ['data_type','BLOCK_NAME','RefName','layer']]
    exe = [arcpy.CreateFeatureclass_management(gdb,str(value[0]),value[1],temp_layer) for value in list_fc_type]


def add_field(fc,field,Type = 'TEXT'):
    TYPE = [i.name for i in arcpy.ListFields(fc) if i.name == field]
    if not TYPE:
        arcpy.AddField_management (fc, field, Type, "", "", 500)



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

    return layer_poly,layer_line,layer_point



# def Get_Attri_blocks_to_dict(df_attri,layer_point):
#     df_attri    = read_excel[~read_excel['LAYER.1'].isnull()]
#     df_attri    = df_attri.set_index('LAYER.1')

#     df_attri['Geom_Type'] = np.where(df_attri['GEOMETRY'] == 'BLOCK','POINT',df_attri['GEOMETRY'])
#     result               = layer_point.df.set_index('Layer').join(df_attri,how='inner')
#     result               = result[(result["Entity"]  ==  'Insert') & (result['BLOCK_NAME.1'] == result['RefName'])]

#     result  = result[["BLOCK_NAME","Geom_Type","FC","BLOCK_NAME.1","SHAPE@"]]
#     dict_   = result.T.to_dict('list')
#     return dict_



# def Connect_attri_layer(dict_attri,dict_poly):
#     intersect = []
#     for key,item in dict_attri.items():
#         if dict_poly.has_key(key):
#             if item[-1].distanceTo(dict_poly[key][-1]) == 0:
#                 intersect.append(key)
#     print "Intersects:", intersect
#     return intersect
