# -*- coding: utf-8 -*-

# for any problem: medadhoze@hotmail.com
# date:    19.10.2021
# version: 3.1

import arcpy,math
import pandas as pd
import numpy as np
import json,datetime,os
from scipy.spatial import distance_matrix
from platform import python_version
arcpy.env.overwriteOutPut = True
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import PyPDF2

arcpy.AddMessage('##############################################')

arcpy.AddMessage('Tools made for Mapi - israel center of mapping')

arcpy.AddMessage('### If any bugs found, contact medad hoze ###')

arcpy.AddMessage('### medadhoze@hotmail.com  ###')

arcpy.AddMessage('### plz Send: 1) Picture of the error, 2) layers, 3) Arcmap version (10.1/10.3/10.5/10.6/10.8/arcpro)  ###')

arcpy.AddMessage('##############################################')



class Layer_Engine():
    '''
    This Engine will transform the layer and its geometry to a pandas dataframe, then will
    check the content of its values
    '''
    def __init__(self,layer,columns = 'all'):
        
        if columns == 'all':
            columns = [f.name.encode('UTF-8') for f in arcpy.ListFields(layer)]
            columns.extend(['SHAPE@AREA'])
            columns.extend(['SHAPE@'])

        self.layer           = layer
        self.gdb             = os.path.dirname  (layer)
        self.name            = os.path.basename (layer)
        self.desc            = arcpy.Describe   (layer)
        self.shapetype       = ShapeType        (self.desc)
        self.oid             = str(self.desc.OIDFieldName)
        self.len_columns     = len(columns)
        self.crs             = self.desc.spatialReference
        self.crs_name        = self.crs.name
        self.data            = [row[:] for row in arcpy.da.SearchCursor (self.layer,columns)]
        self.df              = pd.DataFrame(data = self.data, columns = columns)
        self.df["geom_type"] = self.shapetype
        self.len_rows        = self.df.shape[0]
        self.columns         = columns

        self.data_shape,    self.df_shape , self.Not_closed = None, None, None
        self.exists_curves, self.bad_area   = None, None


    def Count_field(self,field):
        # check the count of all the features in the df
        self.df['count'] = self.df.groupby(field)[field].transform('count')

    def No_shape(self):
        self.No_Shape            = [[i[1],i[2],i[3]] for i in arcpy.da.SearchCursor (self.layer,["SHAPE@",self.oid,'Layer','SHAPE@AREA']) if not i[0]]

    def Extract_shape(self):
        # extract the Geometry of the features
        if self.len_rows > 0:
            if self.shapetype != 'POINT':
                columns_shape            = [self.oid,'X','Y','Layer','Area','SHAPE']
                self.data_shape          = [[i[1],j.X,j.Y,i[2],i[3],i[0]] for i in arcpy.da.SearchCursor (self.layer,["SHAPE@",self.oid,'Layer','SHAPE@AREA']) if i[0] for n in i[0] for j in n if j if n]
                self.df_shape            = pd.DataFrame(data = self.data_shape, columns = columns_shape)
                self.df_shape['index1']  = self.df_shape.index
                self.df_shape['X_Y']     = self.df_shape.apply(lambda row: Connect_rows(row['X'] , row['Y']),axis = 1)
            else:
                columns_shape            = [self.oid,'Layer','Entity','LyrHandle','X','Y']
                self.data_shape          = [[i[1],i[2],i[3],i[4],i[0].labelPoint.X,i[0].labelPoint.Y] for i in arcpy.da.SearchCursor (self.layer,["SHAPE@",self.oid,"Layer","Entity","LyrHandle"]) if i[0]]
                self.df_shape            = pd.DataFrame(data = self.data_shape, columns = columns_shape)
                self.df_shape['X_Y']     = self.df_shape.apply(lambda row: Connect_rows(row['X'] , row['Y']),axis = 1)

    def Filter_point_by_max_distance(self,X_Y,distance):
        # check if the distance of the df are bigger then the distance given
        if self.shapetype == 'POINT':
            if self.data_shape:
                point_data = [[item[4],item[5]] for item in self.data_shape]
                result     = Dis_2arrays_max(point_data,X_Y,distance)
                result     = [i[0] for i in result]
                df2        = self.df_shape.copy()
                df2        = df2[df2['X_Y'].isin(result)]
                return df2
            else:
                print ("Func Extract_shape wasnt activated")
        else:
            print ("Feature isn't POINT")


    def Len_field(self,field,as_int = False):
        # check the len of the fields (later we will check if its bigger then 256)
        if as_int:
            len_field = self.df[field].apply(str).apply(len).astype(int)
            if len_field.shape[0] > 1:
                len_field = len_field[0]
            return int(len_field)
        else:
            self.df[field + '_len'] = self.df[field].apply(len)

    def Filter_df(self,field,Value,Update_df = False):
        # filter a colum from the df
        if Update_df:
            self.df = self.df[self.df[field] == Value]
        else:
            df_filter = self.df[self.df[field] == Value]
            return df_filter


    def Shape_closed(self):
        # check if the shape have a vertex that close the geometry 
        if not isinstance(self.df_shape, type(None)):
            gb_obj            = self.df_shape.groupby (by = self.oid)
            df_min            = gb_obj.agg     ({'index1' : np.min})
            df_max            = gb_obj.agg     ({'index1' : np.max})
            df_edge           = pd.concat      ([df_min,df_max])
            df2               = pd.merge       (self.df_shape,df_edge, how='inner', on='index1')
            df2['Count_X_Y']  = df2.groupby    ('X_Y')['X_Y'].transform('count')
            self.Not_closed   = df2[df2['Count_X_Y'] < 2].values.tolist()

            return self.Not_closed

    def Close_vertxs(self,layer_name,Min_num):
        # check if there is vertexs closer then the mim number given
        '''
        [INFO] - return close vrtxs but only if bigger then 0
        '''
        vertxs              = [[i[1],i[2]] for i in self.data_shape if i[3] == layer_name]
        if self.shapetype != 'POINT' and self.data_shape != None and len(vertxs) < 2000:
            dis_array        = distance_matrix(vertxs,vertxs)
            dis_array        = np.where(dis_array==0, 99999, dis_array) 
            closest_points   = dis_array.argmin(axis = 0)
            close_pnt   = [[str(round(vertxs[i][0],2)) + '-' + str(round(vertxs[i][1],2))\
                             ,vertxs[i],vertxs[closest_points[i]],round(dis_array[i,closest_points[i]],4)]\
                             for i in range(len(vertxs)) if dis_array[i,closest_points[i]] < Min_num and dis_array[i,closest_points[i]] > 0]

            return close_pnt

    def Zero_Area(self):
        # check if there is polygon with geometry area value if 0
        if self.shapetype == 'POLYGON':
            self.bad_area = [[i[4],i[3]] for i in self.data_shape if i[4] <= 0]
            if self.bad_area:
                return self.bad_area
        else:
            self.bad_area = False

            
    def Curves(self,Out_put):
        # check if there is curves in the layers, return True for curves, out put of the curves and the number of curves found
        if self.shapetype in ['POLYGON','POLYLINE']:
            curves_list = [n for i in self.data for n in i if 'describe geometry object' in str(n) if 'curve' in str(json.loads(i[-1].JSON))]
            if curves_list:
                try:
                    arcpy.CopyFeatures_management(curves_list,Out_put)
                except:
                    print_arcpy_message("tool Found: {} Curves, but coudnt copy them".format(len(curves_list)),2)
                self.exists_curves = True
                return len(curves_list)
            else:
                self.exists_curves = False

        return self.exists_curves

    def Check_Block_0_0(self):
        # check if the block have 0,0 coordiates, return a list of the these cooridnates
        Block_at_0_0 = []
        if not self.df.empty:
            if self.shapetype == 'POINT':
                df2 = self.df_shape.copy()
                df2.where  ((df2["X"] < 10) & (df2["X"] > -10) & (df2["Y"] < 10) & (df2["Y"] > -10) & (df2['Entity'] == "Insert"), inplace = True)
                df2 = df2.dropna (axis=0, how='all')
                Block_at_0_0 = df2.values.tolist()
        return Block_at_0_0

    def Check_Columns_letters(self,bad_charc = ['-','"','.']):
        # df.columns[df.columns.str.contains('-|"|.')]   # למה הנקודה תמיד מופיעה כאילו היא קיימת
        cach_fields = False
        try:
            cach_fields = [[field,letter] for field in self.columns for letter in field if letter in bad_charc] # אם ריק אין בעיה עם השדות
        except:
            cach_fields = 'problem with: {} in field, Cant Get the field'  # בעיה עם השדות איך אין אפשרות לדעת למה
        
        return cach_fields

    def Check_Columns_names(self,fields = "SURVEY_YYYY|SURVEY_MM|SURVEY_DD|FINISH_YYYY|FINISH_MM|FINISH_DD"):
        # check the names of the fields, if a name is not found, the tool will return the name.
        exists_columns = set(self.df.columns[self.df.columns.str.contains(fields,na = False)])
        fields_in      = set(fields.split('|'))
        not_exists     = list(fields_in-exists_columns)
        return not_exists

    def Get_Field_Count_to_df(self,field,name_field_count = ''):
        # get the count of items in the column in a new df column, if no name will be given, the field name with _num will be creadted
        if name_field_count == '':
            name_field_count = str(field) + "_num"
        count_data = self.df.groupby(field).size()
        count_data = count_data.to_frame().reset_index()
        count_data = self.df.merge(count_data, on=field).reset_index()
        count_data = count_data.rename(columns={0: name_field_count})
        return count_data

    
    def Dict(self,index_key):
        # convert dataframe to dict
        dict_  = self.df.set_index(index_key)
        dict_2 = dict_.T.to_dict()
        return dict_2


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


def createFolder(dic):
	try:
		if not os.path.exists(dic):
			os.makedirs(dic)
	except OSError:
		print ("Error Create dic")

def Create_Geom_Prob(fgdb_name):
    geom_prob  = fgdb_name + '\\' + 'Geom_prob'
    if not arcpy.Exists(geom_prob):
        arcpy.CreateFeatureclass_management (fgdb_name,'Geom_prob','POINT')
        fields_ = [['Layer','TEXT'],['Handle','TEXT'],['Layer_2','TEXT'],['LyrOn','TEXT'],['LyrFrzn','TEXT']]
        for i in fields_: add_field (geom_prob,i[0],i[1])

    return geom_prob


# def create_layer_from_list(DWG,gdb_name,layer_name,filter_):

#     Out_put = gdb_name + '\\' + layer_name
    

#     columns = [f.name.encode('UTF-8') for f in arcpy.ListFields(DWG)]
#     columns.extend(['SHAPE@'])
#     data            = [row[:] for row in arcpy.da.SearchCursor (DWG,columns,filter_)]

#     if len([i for i in columns if i == b'OBJECTID']) == 0:
#         columns = [b'OBJECTID'] + columns

#     desc            = arcpy.Describe    (DWG)
#     shapetype       = ShapeType         (desc)
#     arcpy.CreateFeatureclass_management (gdb_name,layer_name,shapetype,DWG)
#     insert = arcpy.da.InsertCursor      (Out_put,columns)
#     print_arcpy_message(columns)
#     insertion = [insert.insertRow       ([value]) for value in data]

def Main_0_0_Error(obj_blocks,id_prob_excel = "E_BLOCK_2",message = "you have blocks at coordinates 0,0"):
    blocks_ = []
    at_Zero_Zero = obj_blocks.Check_Block_0_0()
    if len(at_Zero_Zero) > 0:
        print_arcpy_message ('you have blocks at coordinates 0,0',2)
        blocks_.append       ([id_prob_excel,message])
        start = 0
        for i in at_Zero_Zero:
            blocks_.append       ([str(start),'layer: {}, have blocks at coordinates 0,0'.format(i[1])])
            print_arcpy_message('block: {}'.format(str(i)),2)
            start += 1
    return blocks_


def Erase(fc,del_layer,Out_put = ''):

    '''
    fc        = השכבה הראשית- שכבה ממנה רוצים למחוק
    del_layer = שכבה שתמחק את השכבה הראשית
    Out_put   = שכבת הפלט, במידה ולא תוכנס שכבה, ימחק מהשכבה הראשית
    '''
    arcpy.RepairGeometry_management(fc)
    arcpy.RepairGeometry_management(del_layer)
    
    desc = arcpy.Describe(fc)

    if not Out_put == '':
        fc = arcpy.CopyFeatures_management(fc,Out_put)
    else:
        Out_put = fc
    
    if desc.ShapeType == u'Point':
        del_layer_temp = 'in_memory' + '\\' + 'Temp'
        arcpy.Dissolve_management(del_layer,del_layer_temp)
        if desc.ShapeType == u'Point':
            geom_del = [row.shape for row in arcpy.SearchCursor (del_layer_temp)][0]
            Ucursor  = arcpy.UpdateCursor (Out_put)
            for row in Ucursor:
                point_shape = row.shape.centroid
                if geom_del.distanceTo(point_shape)== 0:
                    Ucursor.deleteRow(row)
                else:
                    pass
            del Ucursor
        del del_layer_temp
                        
    else:
        dissolve = False
        count_me = int(str(arcpy.GetCount_management(del_layer)))
        if count_me > 0:
            
            temp = 'in_memory' +'\\'+'_temp'
            try:
                arcpy.Dissolve_management(del_layer,temp)
                dissolve = True
            except:
                temp = del_layer

            if int(str(arcpy.GetCount_management(temp))) > 0:
                geom_del = [row.shape for row in arcpy.SearchCursor (temp)][0]
                Ucursor  = arcpy.UpdateCursor (Out_put)
                for row in Ucursor:
                    geom_up     = row.shape
                    new_geom    = geom_up.difference(geom_del)
                    try:
                        row.shape = new_geom
                        Ucursor.updateRow (row)
                    except:
                        pass
                del Ucursor
            if dissolve:
                arcpy.Delete_management(temp)
        else:
            pass

                    
    arcpy.RepairGeometry_management(Out_put)
    return Out_put


def Extract_dwg_to_layer(fgdb_name,DWF_layer,layer_name,Filter = ''):
    # convert DWG to a GDB layer
    try:
        fc_out_line   = str(arcpy.FeatureClassToFeatureClass_conversion( DWF_layer, fgdb_name, layer_name, Filter))
        return fc_out_line
    except:
        msg = r"Coudnt Make FeatureClassToFeatureClass_conversion for layers {}".format(layer_name)
        # fc_out_line = create_layer_from_list(DWF_layer,fgdb_name,layer_name,Filter)
        print_arcpy_message(msg,2)
        return DWF_layer
        

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

    # [INFO] - check if the CAD have been saved in the right version
    # works for arcPro and ArcGis diffrently so there is 2 methods on try and except.

	dictme = {'AC1014':'AutoCAD Release 14','AC1015': 'AutoCAD2000','AC1018': 'AutoCAD2004','AC1021': 'AutoCAD2007','AC1024': 'AutoCAD2010','AC1027': 'AutoCAD2013','AC1032': 'AutoCAD2018'}
	if (str(python_version())) == '2.7.16': # Arcmap
		x = open(DWG,'r').read(6)
	else:
		file1 = open(DWG,errors='ignore')
		x     = file1.readline()[:6]
	cheak_version = []
	try:
		version = [i for n,i in dictme.items() if x == n]
	except:
		print_arcpy_message  ("coudent exctract DWG version",status = 2)
		cheak_version.append (["E_Version_1","coudent exctract DWG version"])
	
	bad_ver = ['AutoCAD2000','AutoCAD2013','AutoCAD2018','AutoCAD Release 14']
	
	if version[0] in bad_ver:
		print_arcpy_message  ("the CAD version is {}, and is not supported".format(version[0]),status = 2)
		cheak_version.append (["E_Version_2","the CAD version is {}, and is not supported".format(version[0])])
	else:
		print_arcpy_message("the CAD version is {}".format(version[0]),status = 1)

	return cheak_version


def Create_Polygon_From_Line(polyline,Out_put,fillter,field_name):
    '''
    [INFO] - Create polygon from vertexs
    return polygon
    '''
    arcpy.CopyFeatures_management(arcpy.Polygon(arcpy.Array([arcpy.Point(j.X,j.Y) for i in arcpy.SearchCursor (polyline,fillter) for n in i.shape for j in n if j])),Out_put)
    # arcpy.AddField_management        (Out_put,'Layer','TEXT')
    # arcpy.CalculateField_management  (Out_put,"Layer", field_name, "PYTHON_9.3")

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
    '''
    [INFO] - calculte distance of 2 points
    '''
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
        declaration.append  (["E_Decleration_2","No Declaration Found"])
        return declaration
    elif obj_declar.len_rows > 1:
        print_arcpy_message ("you have {} declarations, only 1 is approved".format(obj_declar.len_rows),2)
        declaration.append  (["E_Declaration_1","you have {} declarations, only 1 is approved".format(obj_declar.len_rows)])

    # check if distance to line is bigger then 100,000 meters
    distance = Check_distance_data_shape(obj_declar.data_shape,obj_line.data_shape)
    if distance > 100000:
        print_arcpy_message ("Declaration found to be far from M1300",2)
        declaration.append  (["E_Decleration_3","Declaration found to be far from M1300"])

    # check if missing values in: SURVEYOR, ACCURACY_HOR , ACCURACY_VER

    def missing_digi_in_field(df,field_name):
        '''
        [INFO] - check if all values in field are numarics, if not return en error
        '''
        declar = []
        if field_name in df.columns:
            data = pd.to_numeric(df[field_name], errors='coerce').notnull().all()
            if not data:
                print_arcpy_message('field {} in declaration have no Value'.format(field_name),status = 2)
                declar.append(['E_Declaration_4','field: ' + str(field_name) + ' in declaration have no value inside'])
        else:
            declar.append(['E_Declaration_4','field: ' + str(field_name) + ' in declaration have no value inside'])
            print_arcpy_message('Field: {} Does not found'.format(field_name))
            
        return declar


    SURVEYOR     = missing_digi_in_field(obj_declar.df,b"SURVEYOR")
    ACCURACY_VER = missing_digi_in_field(obj_declar.df,b"ACCURACY_VER")
    ACCURACY_HOR = missing_digi_in_field(obj_declar.df,b"ACCURACY_HOR")

    if SURVEYOR:
        declaration.append(SURVEYOR[0])
    if ACCURACY_VER:
        declaration.append(ACCURACY_VER[0])
    if ACCURACY_HOR:
        declaration.append(ACCURACY_HOR[0])

    # check the number of values in dates fields, if values are not valid, will return an error

    obj_declar.Filter_df(b"Entity",'Insert',True)
    list_fileds    = obj_declar.columns
    field_must     = [b'SURVEY_YYYY',b'SURVEY_MM',b'SURVEY_DD',b'FINISH_YYYY',b'FINISH_MM',b'FINISH_DD']
    missing_fields = [i for i in field_must if i not in list_fileds]
    if missing_fields == []:
        one_two = [1,2]
        if int(str(arcpy.GetCount_management(obj_declar.layer))) > 0:
                data_date = [obj_declar.Len_field(field,as_int = True) for field in field_must]
                if data_date[0] != 4:
                        print_arcpy_message("there is {} numbers in field: SURVEY_YYYY, 4 needed".format(str(data_date[0]),status = 2))
                        declaration.append(["E_Decleration_6","there is {} numbers in field: SURVEY_YYYY, 4 needed".format(data_date[0])])
                if data_date[1] not in one_two:
                        print_arcpy_message("there is {} numbers in field: SURVEY_MM, 2 needed".format(str(data_date[1])),status = 2)
                        declaration.append(["E_Decleration_6","there is {} numbers in field: SURVEY_MM, 2 exepted".format(data_date[1])])
                if data_date[2] not in one_two:
                        print_arcpy_message("there is {} numbers in field: SURVEY_DD, 2 needed".format(str(data_date[2])),status = 2)
                        declaration.append(["E_Decleration_6","there is {} numbers in field: SURVEY_DD, 2 exepted".format(data_date[2])])
                if data_date[3] != 4:
                        print_arcpy_message("there is {} numbers in field: FINISH_YYYY, 4 needed".format(str(data_date[3])),status = 2)
                        declaration.append(["E_Decleration_6","there is {} numbers in field: FINISH_YYYY, 4 needed".format(data_date[3])])
                if data_date[4] not in one_two:
                        print_arcpy_message("there is {} numbers in field: FINISH_MM, 2 needed".format(str(data_date[4])),status = 2)
                        declaration.append(["E_Decleration_6","there is {} numbers in field: FINISH_MM, ,2  exepted".format(data_date[4])])
                if data_date[5] not in one_two:
                        print_arcpy_message("there is {} numbers in field: FINISH_DD, 2 exepted".format(str(data_date[5])),status = 2)
                        declaration.append(["E_Decleration_6","there is {} numbers in field: FINISH_DD, 2 needed".format(data_date[5])])
        else:
                print_arcpy_message("layer 'declaration' have no features",status = 2)
                declaration.append(["E_Decleration_7","layer 'declaration' have no features"])
    else:
            fields_msg = ''.join([str(i)[1:] + '-' for i in missing_fields])[0:-1]
            print_arcpy_message("layer 'declaration' missing fields: {}".format(fields_msg),status = 2)
            declaration.append(["E_Decleration_5","Missing fields"])
            declaration.append(["E_Declaration_5",fields_msg])

    return declaration


def Check_Blocks (obj_blocks,Point,obj_poly,Line_object,fgdb_name):
    
    # chack if there is -,",.  in the fields names, if found, return the block name and layer of the field with the bad chracter
    blocks     = []
    bad_blocks = []
    bad_charc     = ['-','"','.']
    cach_fields = [str(i.name) for i in arcpy.ListFields(Point) for n in i.name if n in bad_charc]
    if cach_fields:
        cach_fields.insert(0,'RefName')
        cach_fields.insert(0,'Layer')
        bad_blocks.append('  ///  '.join([i for i in list(set(['Layer:  ' + str(row[0]) +',  Block:  '+str(row[1])  for row in arcpy.da.SearchCursor(Point,cach_fields) for n in row[2:] if n]))]))

        if bad_blocks:
            cach_fields = ','.join([i for i in cach_fields[2:]])[1:]
            print_arcpy_message ("{}  ----->   fields: {}".format(bad_blocks[0],cach_fields),2)
            blocks.append       (["E_BLOCK_3","{}  ----->   Fields: {}".format(bad_blocks[0],cach_fields)])


    # check if there is block in coordinate 0,0

    blocks_0_0 = Main_0_0_Error(obj_blocks)
    blocks = blocks + blocks_0_0
            
    # Check if there if blocks outside M1300
    if arcpy.Exists(obj_poly.layer):
        arcpy.MakeFeatureLayer_management           (obj_blocks.layer,'block_lyr')
        arcpy.SelectLayerByLocation_management      ('block_lyr','INTERSECT',obj_poly.layer,0.01,'','INVERT')
        data = [[i[0],i[1],str(round(i[0].centroid.X,1)) + '-' + str(round(i[0].centroid.Y,1)),i[2],i[3],i[4]] for i in arcpy.da.SearchCursor ('block_lyr',['SHAPE@','Layer','Handle','LyrOn','LyrFrzn']) if i[0]]
        if data:
            print_arcpy_message ('blocks outside the M1300 area',2)
            blocks.append       (["E_BLOCK_1",'blocks outside the M1300 area'])
            Geom_prob = Create_Geom_Prob                (fgdb_name)
            insert    = arcpy.da.InsertCursor           (Geom_prob,['Layer','SHAPE@','Handle','Layer_2','LyrOn','LyrFrzn'])
            insertion = [insert.insertRow               (['Block layer: {}'.format(value[1]),value[0],value[3],value[1],value[4],value[5]]) for value in data]
            start_me = 0
            for i in data:
                blocks.append       (["E_BLOCK_1",str(start_me)+'- layer: {}, have coordinates at  {}'.format(i[1],i[2])])
                print_arcpy_message ('layer: {}, have coordinates at  {}'.format(i[1],i[2]),2)
                start_me += 1
    else:
        # if no poly M1300 Exists, checks distance from Lines M1300
        print_arcpy_message ('Didnt find polygon M1300 working on lines',2)
        x_y       = [[i[1],i[2]] for i in Line_object.data_shape]
        if x_y[0]:
            far_point = obj_blocks.Filter_point_by_max_distance([x_y[0]],500)  # enough chacking 1 vertex of line to know if block is to far
            far_point = far_point[['Layer','Entity','X_Y']][((far_point['X'] != 0.0) | (far_point['Y'] != 0.0)) & (far_point['Entity'] == 'Insert')].values.tolist()
            if len(far_point) > 0:
                print_arcpy_message ('blocks outside the M1300 area',2)
                blocks.append       (["E_BLOCK_1",'blocks outside the M1300 area'])
                start_me = 0
                for i in far_point:
                    blocks.append       (["E_BLOCK_1",str(start_me)+'- layer: {}, block name: {}, have coordinates at  {}'.format(i[0],i[1],i[2])])
                    print_arcpy_message ('layer: {}, block name: {}, have coordinates at  {}'.format(i[0],i[1],i[2]),2)
                    start_me += 1


    # Check DEC_AREA_TBL item in point layer
    # new_df   = obj_blocks.Filter_df(b"Layer","DEC_AREA_TBL")
    # len_rows = new_df.shape[0]
    # if len_rows > 1:
    #     print_arcpy_message ('There is {} features called: "DEC_AREA_TBL", only 1 excepted'.format(str(len_rows)),2)
    #     blocks.append       (['E_BLOCK_4','There is {} features called: "DEC_AREA_TBL", only 1 excepted'.format(str(len_rows))])
    # if len_rows > 0:
    #     Gush_not_int = new_df.loc[~new_df[b'GUSH'].astype(str).str.isdigit()  ,b'GUSH'].tolist()
    #     parc_not_int = new_df.loc[~new_df[b'PARCEL'].astype(str).str.isdigit(),b'GUSH'].tolist()

    #     del_char_if_in_list(Gush_not_int,'/')
        
    #     if Gush_not_int:
    #         print_arcpy_message ('at feature DEC_AREA_TBL, There is unexpected letters in gush field: {}, only numbers allowed'.format(str(Gush_not_int)),2)
    #         blocks.append       (['E_BLOCK_6','leters in DEC_AREA_TBL: {}'.format(str(Gush_not_int))]) 
    #     if parc_not_int:
    #         print_arcpy_message ('at feature DEC_AREA_TBL, There is unexpected letters in parcel field: {}, only numbers allowed'.format(str(parc_not_int)),2)
    #         blocks.append       (['E_BLOCK_6','leters in DEC_AREA_TBL: {}'.format(str(parc_not_int))])    
    # else:
    #     print_arcpy_message('No feature DEC_AREA_TBL was Found in the point layer',2)
    #     blocks.append      (['E_BLOCK_5','No feature DEC_AREA_TBL was Found in the point layer'])

    return blocks




def Check_Lines(obj_lines,Lines_all,poly_M1200_M1300,fgdb_name):

    lines,geom_list                 = [],[]
    close_pnt_m1300,close_pnt_m1200 = False,False

    # check if there is self intersect of vertxs
    if obj_lines.df[obj_lines.df['Layer'] == 'M1200'].values.tolist():
        close_pnt_m1200 = obj_lines.Close_vertxs('M1200',0.1)
    if obj_lines.df[obj_lines.df['Layer'] == 'M1300'].values.tolist():
        close_pnt_m1300 = obj_lines.Close_vertxs('M1300',0.1)

    if close_pnt_m1200:
        print_arcpy_message('Layer M1200 with bad geometry',2)
        lines.append       (["E_1200_3","Layer M1200 with bad geometry"])
        start_num = 0
        for i in close_pnt_m1200:
            print_arcpy_message ('M1200 vertxs = {}'.format(str(i)),2)
            lines.append        ([str(start_num),'M1200 vertxs = {}'.format(str(i))])
            geom_list.append    (['M1200',i[1][0],i[1][1]])
            start_num +=1

    if close_pnt_m1300:
        print_arcpy_message('Layer M1300 with bad geometry',2)
        lines.append       (["E_1300_3","Layer M1300 with bad geometry"])
        start_ = 0
        for i in close_pnt_m1300:
            print_arcpy_message  ('M1300 vertxs = {}'.format(str(i)))
            lines.append         ([str(start_),'M1300 vertxs = {}'.format(str(i))])
            geom_list.append     (['M1300',i[1][0],i[1][1]])
            start_ +=1


    # check Curves 
    obj_lines.Curves(obj_lines.layer + '_Curves')
    if obj_lines.exists_curves:
        print_arcpy_message('You have curves in layer M1200 or M1300',2)
        lines.append       (["E_Curves",'You have curves in layer M1200 or M1300'])

    # check more then 1 - M1200 or M1300
    M1200 = obj_lines.Filter_df('Layer','M1200')
    M1300 = obj_lines.Filter_df('Layer','M1300')
    if M1200.shape[0] > 1:
        print_arcpy_message("you have {} M1200,  1 is expected".format(str(M1200.shape[0])),2)
        lines.append       (["E_1200_2","you have {} M1200,  1 is expected".format(str(M1200.shape[0]))])

    if  M1200.shape[0] == 0:
        print_arcpy_message("Layer M1200 is missing",2)
        lines.append       (["E_1200_1","Layer M1200 is missing"])

    if M1300.shape[0] > 1:
        print_arcpy_message("you have {} M1300,  1 is expected".format(str(M1300.shape[0])),2)
        lines.append       (["E_1300_2","you have {} M1300,  1 is expected".format(str(M1300.shape[0]))])

    if M1300.shape[0] == 0:
        print_arcpy_message("Layer M1300 is missing",2)
        lines.append       (["E_1300_1","Layer M1300 is missing"])


    # check if line are not closed
    obj_lines.Shape_closed()
    if obj_lines.Not_closed:
        print_arcpy_message ('there is vertexs that are not closed',2)
        lines.append        (['E_1200_4','there is vertexs that are not closed'])
        num_ = 1
        for i in obj_lines.Not_closed:
            print_arcpy_message ('vertx that is not closed: {}'.format(i),2)
            lines.append        ([str(num_),'vertx that is not closed: {}'.format(i)])
            geom_list.append    (['M1200\M1300',i[1],i[2]])
            num_ += 1

    if geom_list:
        geom_prob = Create_Geom_Prob(fgdb_name)
        insert    = arcpy.da.InsertCursor   (geom_prob,['Layer','SHAPE@'])
        insertion = [insert.insertRow       ([value[0],arcpy.Point(value[1],value[2])]) for value in geom_list]


    # Check if there is NoType shape 
    line_all_class  = Layer_Engine(Lines_all)
    line_all_class.No_shape()
    
    if line_all_class.No_Shape:
        print_arcpy_message                     ("found Lines That dosent have shape",2)
        for i in line_all_class.No_Shape: print_arcpy_message ("there is feature with no shape at layer: {}".format(i[1]),2)
        message = ','.join(i[1] for i in line_all_class.No_Shape)[1:]
        lines.append                            (["E_Line_1","Features with shape NoType at layers: {}".format(message)])

    # check if line intersect with M1300

    if arcpy.Exists(poly_M1200_M1300) and not os.path.dirname(Lines_all).endswith('.dwg'):
        Erase(Lines_all,poly_M1200_M1300)
    if int(str(arcpy.GetCount_management(Lines_all))) and not os.path.dirname(Lines_all).endswith('.dwg'):
        line_prob = fgdb_name + '\\' + 'Line_prob'
        arcpy.MakeFeatureLayer_management       (obj_lines.layer,'M1300_lyr',"Layer = 'M1300'")
        arcpy.MakeFeatureLayer_management       (Lines_all,'Lines_all_lyr',"Layer NOT IN ('M1300','M1200')")
        arcpy.SelectLayerByLocation_management  ("Lines_all_lyr","INTERSECT","M1300_lyr",0.1)
        arcpy.Select_analysis                   ("Lines_all_lyr",line_prob)

        data_error = str(list(set([row[0] for row in arcpy.da.SearchCursor(line_prob,['Layer'])])))[1:-1] 

        print_arcpy_message                     ("found Lines Cuting M1300 at layers: {}".format(data_error),2)
        lines.append                            (["E_1300_4","found Lines Cuting M1300 at layers: {}".format(data_error)])

    if arcpy.Exists(Lines_all) and not os.path.dirname(Lines_all).endswith('.dwg'):
        arcpy.Delete_management                 (Lines_all)


    return lines

def Create_CSV(data,csv_name):
    df        = pd.DataFrame(data,columns = ["Error Key", "Error"])
    df = df.set_index("Error Key")
    df.to_csv(csv_name)



def mxd_pdf_making(mxd_path,gdb_path,name,gdb,folder):

    # creating pdf for arcmap

    if (str(python_version())) == '2.7.16':

        mxd = arcpy.mapping.MapDocument    (mxd_path)
        mxd.findAndReplaceWorkspacePaths   (gdb_path, gdb)

        df           = arcpy.mapping.ListDataFrames  (mxd)[0]
        BORDER_Layer = arcpy.mapping.ListLayers      (mxd, "", df)[-1]
        df.extent    = BORDER_Layer.getExtent        ()

        mxd.saveACopy     (gdb + "\\Cheack_"+name+".mxd")
        arcpy.AddMessage  ("Open MXD Copy")
        # os.startfile      (gdb + "\\Cheack_"+name+".mxd")
        
        arcpy.mapping.ExportToPDF(mxd,folder +r"\\Report_"+name+".pdf")
        del mxd


def Create_Pdfs(mxd_path,gdb_Tamplate,gdb_path,pdf_output):

    # create pdf for ArcPro

    pdf_output = add_endwith(pdf_output,endswith_ = '.pdf')

    p = arcpy.mp.ArcGISProject (mxd_path)
    p.updateConnectionProperties(gdb_Tamplate, gdb_path)

    # get 1 of the layers for zoom in
    m   = p.listMaps('Map')[0]
    lyr = m.listLayers()[6]

    delete_templates = [m.removeLayer(i) for i in m.listLayers() if ('Tamplates' in i.dataSource)]

    lyt = p.listLayouts    ("Layout1")[0]
    mf  = lyt.listElements ('MAPFRAME_ELEMENT',"Map Frame")[0]
    mf.camera.setExtent    (mf.getLayerExtent(lyr,False,True))
    mf.camera.scale = mf.camera.scale*1.8

    name = os.path.basename(pdf_output).split('.')[0]
    DT = lyt.listElements ('TEXT_ELEMENT')
    for i in DT:
        if i.name == 'name':
            i.text = name

    lyt.exportToPDF(pdf_output)


def Create_line_prob(path_geom_probm,lines,block_as_line,Create_line_prob):
    frozen_layers = []
    if int(str(arcpy.GetCount_management(path_geom_probm))):
        far_blocks  = [[row[0],row[1],row[2]] for row in arcpy.da.SearchCursor(path_geom_probm,['Handle','LyrFrzn','LyrOn','Layer_2']) if row[0]]
        if Create_line_prob:
            # combine bad blocks with blocks that dosent pass to GDB, (do we need to delete the blocks that disnt go to gdb on if they are out of M1300)
            far_blocks.extend(Create_line_prob)
        if far_blocks:
            # find the line layers connected with the far blocks and the blocks that didnt pass to gdb
            handels     = ",".join(["'"+i[0]+"'" for i in far_blocks])
            if arcpy.Exists(lines):
                arcpy.Select_analysis                   (lines,block_as_line,"\"Handle\" in ("+handels+")")
            else:
                print_arcpy_message('You have froozen and TurnOff layers at habdeles: {}'.format(handels),2)
        
        froozen = [i for i in far_blocks if i[1] == 1 or i[2] == 0]
        if froozen:
            for j in froozen:
                print_arcpy_message('frozen or layer Off at: {}, turn On or unfrozen the layer'.format(j[3]),2)
                frozen_layers.append('frozen or layer Off at: {}, turn On or unfrozen the layer'.format(j[3]))
    return frozen_layers
        

def Cheak_CADtoGeoDataBase(DWG,fgdb_name,obj_block):	
    # checking if arcpy can make layer to Geodatabase
	CADtoGeoDataBase = []
	create_CAD_conv  = False
	geom_prob        = fgdb_name + '\\' + 'Geom_prob'
	data_set         = fgdb_name + '\\' + 'chacking'
	line_from_dst    = data_set  + '\\' + 'Polyline'
	block_as_line    = fgdb_name + '\\' + 'Lines_from_blocks'

	try:
		arcpy.CADToGeodatabase_conversion(DWG,fgdb_name,'chacking',1)
		print_arcpy_message   ("tool made CAD to Geodatabase" , status = 1)
		create_CAD_conv = True
	except:
		print_arcpy_message("tool didnt made CAD to Geodatabase" , status = 0)
		CADtoGeoDataBase.append(["E_FC_1",'tool didnt made CAD to Geodatabase'])


    # check declaration in Geodatabase
	layer_cheacking = fgdb_name + '\\' + 'chacking\Point'
	if arcpy.Exists(layer_cheacking):
		decl_list = [row[0] for row in arcpy.da.SearchCursor(layer_cheacking,["Layer"]) if row[0] in ('declaration','DECLARATION')]
		if len(decl_list) > 1 or len(decl_list) == 0:
		    massage = "layer declaration from chacking\point (Geodatabase) found {} declaration, must be 1 ".format(len(decl_list))
		    print_arcpy_message(massage, status = 2)
		    CADtoGeoDataBase.append(["E_Declaration_8",massage])

    # # Check if there is blocked that pass DWG to geo database but not feature class to feature class
	blockes_dosent_pass = []
	if create_CAD_conv:
		points   = data_set  + '\\' + 'Point'
		check    = fgdb_name + '\\' + 'Check_geom'
		Filter_  = "\"Entity\" = 'Insert'"
        
		arcpy.Select_analysis                  (points,check,Filter_)
		arcpy.MakeFeatureLayer_management      (check,'check_lyr')
		arcpy.SelectLayerByLocation_management ('check_lyr','INTERSECT',obj_block.layer,0.1)
		arcpy.DeleteFeatures_management        ('check_lyr')

		num = int(str(arcpy.GetCount_management(check)))
		if num > 0:
		    print_arcpy_message     ('TOTAL {} blocks didnt pass convert to layer'.format(num),2)

		    massage  = "There is: {} Blocks that dosent pass to GDB".format(num)
		    CADtoGeoDataBase.append(["E_BLOCK_7",massage])
		    blockes_dosent_pass = [row for row in arcpy.da.SearchCursor(check,['Handle','LyrFrzn','LyrOn','Layer']) if row[3]]
		    for i in blockes_dosent_pass: CADtoGeoDataBase.append(["E_BLOCK_7",'block in layer: {}'.format(i[3])])

		check_obj = Layer_Engine(check)
		check_obj.Extract_shape()
		blocks_0_0 = Main_0_0_Error(check_obj,'','Blocks at 0,0 that didnt pass "CADToGeodatabase_conversion" tool')
		CADtoGeoDataBase = CADtoGeoDataBase + blocks_0_0
                
		if blockes_dosent_pass:
		    On_layers = list(set([row[3] for row in arcpy.da.SearchCursor(check,['Handle','LyrFrzn','LyrOn','Layer']) if row[3]]))
		    text_me   = ','.join([i for i in set(On_layers)])
		    CADtoGeoDataBase.append(["E_BLOCK_7",'total blook that didnt pass: {}, in layers: {}'.format(len(blockes_dosent_pass),text_me)])
		    # fields          = ['SHAPE@','Entity','Handle','Layer','LyrFrzn','LyrOn']
		    # Missing_blocks  = [row for row in arcpy.da.SearchCursor(check,fields)]

	if arcpy.Exists(geom_prob): 
		frozen_layer = Create_line_prob (geom_prob,line_from_dst,block_as_line,blockes_dosent_pass)
		for i in frozen_layer:
		    if i:
		        CADtoGeoDataBase.append(['E_BLOCK_8',i])
    
	return CADtoGeoDataBase


def Create_text_Prob(fgdb_name,name):
    text_prob  = fgdb_name + '\\' + name
    if not arcpy.Exists(text_prob):
        arcpy.CreateFeatureclass_management (fgdb_name,name,'POINT')
        fields_ = [['Layer','TEXT'],['Style','TEXT'],['Entity','TEXT']]
        for i in fields_: add_field (text_prob,i[0],i[1])

    return text_prob


def Get_wrong_text_style(anno,gdb,Wrong_text):

    prob = []

    anno_class = Layer_Engine(anno)

    anno_class.Filter_df(b'Entity','Text',True)

    anno_class.df = anno_class.df[anno_class.df[b'Style'].isin(Wrong_text)]

    if anno_class.df.shape[0]:

        print_arcpy_message ('HAVING Wrong TEXT foramt',2)

        text_prob = Create_text_Prob (gdb,'text_prob')
        Gropyby   = anno_class.df.groupby(b'Style')[b'Layer'].apply(set).reset_index(name='Layer')
        data      = anno_class.df[[b'Layer','SHAPE@',b'Entity',b'Style']].values.tolist()

        data_print = Gropyby.values.tolist()
        for i in data_print:
            message = 'Wrong text style: ' + i[0] + ', in layers: ' + ''.join(i for i in str(i[1]) if i not in ('{','}'))
            print_arcpy_message (message,2)
            prob.append(["E_Annotation_3",message])


        insert    = arcpy.da.InsertCursor           (text_prob,['Layer','SHAPE@','Entity','Style'])
        insertion = [insert.insertRow               ([value[0],value[1],value[2],value[3]]) for value in data]

        return prob


def Annotation_problems(DWG,gdb):
        # check if there is more then 254 chractes in a field.
		long_prob = []
		anno  = DWG +'\\' + 'Annotation'
		x = [[row[0],row[1],row[2],row[3]] for row in arcpy.da.SearchCursor (anno,['Layer','TxtMemo','Entity','RefName'])]
		for i in x:
			if (len(i[1]) > 254) or (len(i[2]) > 254) or (len(i[3]) > 254):
				print_arcpy_message("{} is with more then 254 characters, plz notice".format(str(i[0])),status = 2)
				long_prob.append   (["E_Annotation","{} is with more then 254 characters".format(i[0])])

        # check if thhere is 'MTEXT' type in layer
		mtext = [i[0] for i in x for n in i if n.upper() == 'MTEXT']
		if mtext:
			mtext_layers = ','.join([i for i in set(mtext)])
			print_arcpy_message("There is MText in layers: {}, no Mtext is allowed".format(mtext_layers),2)
			long_prob.append   (["E_Annotation_2","There is MText in layers: {}, no Mtext is allowed".format(mtext_layers)])

		# prob = Get_wrong_text_style(anno,gdb,Wrong_text = ['miryl'])
		# long_prob = long_prob + prob
				
		return long_prob


def add_field(fc,field,Type = 'TEXT'):
    TYPE = [i.name for i in arcpy.ListFields(fc) if i.name == field]
    if not TYPE:
        arcpy.AddField_management (fc, field, Type, "", "", 500)


def add_endwith(json_path,endswith_):
    if not os.path.basename(json_path).endswith(endswith_):
        return json_path + endswith_
    else:
        return json_path


def Creare_report_From_CSV(path = '',path_result = '',del_extra_report = True):
    if not path == '' or path_result == '':
        # reading the tamplate csv, and prepare before joining
        save_name   = path_result
        path        = pd.read_csv    (path,encoding="ISO-8859-8")
        path        = path.set_index ("Error_ID")

        # reading the tool csv after checking the DWG
        try:
            path_result = pd.read_csv(path_result,encoding="ISO-8859-8")
        except:
            path_result = pd.read_csv(path_result,encoding="utf-8")
        path_result = path_result.set_index("Error Key")

        # Create new CSV that contains the tamplate csv with hebrew and the tool csv with the correct errors
        result      = path.join(path_result, how="inner")
        path,name   = os.path.split(save_name)
        new_csv     = path + '\\' + name.split('.')[0] + '_report.csv'

        #  # # # #export to csv
        # result.to_csv(new_csv,encoding="ISO-8859-8")

        if del_extra_report:
            os.remove(save_name)

        return result

def fix_name(name):
    # make sure there is no spaces in DWG name 
    conti = True
    check_name = os.path.basename(name).split('.')[0]
    if ' ' in check_name:
        f = check_name.find(' ')
        print_arcpy_message("file name: {} have spaces, No spaces in DWG name".format(check_name),2)
        conti = False
    return conti

def del_char_if_in_list(list_,char):
    exe = [list_.remove(i) for i in list_ if char in i if len(i) > 1]


def Get_df_to_pdf(df,pdf_table):

    fig, ax =plt.subplots(figsize=(13,9))
    ax.axis('tight')
    ax.axis('off'  )

    df['שגיאה ודרך פתרון'] = df.loc[:,'שגיאה ודרך פתרון'].apply(lambda x: x[::-1])

    df['שגיאה ודרך פתרון'] = df['שגיאה ודרך פתרון'].replace({'0031M':'M1300', '0021M':'M1200','4002':'2004','0002':'2000','8102':'2018',\
                                                                '4102':'2014','01020':'2010','8002':'2008','TXETM':'MTEXT','TXET':'TEXT','452':'254',\
                                                                'LBT_AERA_CES':'DEC_AREA_TBL','noitarelced':'decleration','ROH_YCARUCCA':'ACCURACY_HOR',\
                                                                'REV_YCARUCCA':'ACCURACY_VER','ROYEVRUS':'SURVEYOR','TXETBEH':'HEBTEXT'},regex=True)


    str_ = 'שגיאה ודרך פתרון'
    df   = df.rename(columns = {str_:str_[::-1]})

    try:
        the_table = ax.table(cellText=df.values,colLabels=df.columns,loc='center')
    except:
        print_arcpy_message("no Rows Found")

    pp = PdfPages(pdf_table)
    pp.savefig(fig, bbox_inches='tight')
    pp.close()


def MergaePdfs(pfd1,pdf2,output_pdf):
    # Open the files that have to be merged one by one
    pdf1File = open(pfd1, 'rb')
    pdf2File = open(pdf2, 'rb')
    
    # Read the files that you have opened
    pdf1Reader = PyPDF2.PdfFileReader(pdf1File)
    pdf2Reader = PyPDF2.PdfFileReader(pdf2File)
    
    # Create a new PdfFileWriter object which represents a blank PDF document
    pdfWriter = PyPDF2.PdfFileWriter()
    
    # Loop through all the pagenumbers for the first document
    for pageNum in range(pdf1Reader.numPages):
        pageObj = pdf1Reader.getPage(pageNum)
        pdfWriter.addPage(pageObj)
    
    # Loop through all the pagenumbers for the second document
    for pageNum in range(pdf2Reader.numPages):
        pageObj = pdf2Reader.getPage(pageNum)
        pdfWriter.addPage(pageObj)
    
    # Now that you have copied all the pages in both the documents, write them into the a new document
    pdfOutputFile = open(output_pdf, 'wb')
    pdfWriter.write(pdfOutputFile)
    
    # Close all the files - Created as well as opened
    pdfOutputFile.close()
    pdf1File.close()
    pdf2File.close()



def Check_coordinate_system(blocks,lines_M,poly_M):
    prob_crs      = []
    crs_check_bad = []
    for i in [blocks.crs_name,lines_M.crs_name,poly_M.crs_name]:
        if i not in ['Israel_TM_Grid','Unknown']:
            crs_check_bad.append(i)

    if crs_check_bad:
        bad_crs = list(set(crs_check_bad))[0]
        print_arcpy_message("DWG with bad CRS, name: {}, plz use NEW israel or no CRS".format(bad_crs),status = 2)
        prob_crs.append   (["E_CRS_1","DWG with bad CRS, name: {}, plz use NEW israel or no CRS".format(bad_crs)])    
    else:
        coordinate_system = arcpy.SpatialReference(2039)
        arcpy.env.outputCoordinateSystem = coordinate_system
    return prob_crs


print_arcpy_message('#  #  #  #  #     S T A R T     #  #  #  #  #')

# # # In Put # # #
DWGS        = arcpy.GetParameterAsText(0).split(';')
# DWGS = [r"C:\Users\Administrator\Desktop\medad\python\Work\Engine_Cad_To_Gis\DWG\6157-269.dwg"]


# # #     Preper Data    # # #
scriptPath     = os.path.abspath (__file__)
folder_basic   = os.path.dirname (scriptPath)
Tamplates      = folder_basic + "\\" + "Tamplates"
GDB_file       = folder_basic + "\\" + "Temp"
csv_errors     = Tamplates    + "\\" + "Errors_Check_DWG.csv"

for DWG in DWGS:
    conti = fix_name(DWG)
    if conti:
        print_arcpy_message (DWG,1)
        DWG_name       = os.path.basename(DWG).split(".")[0]
        fgdb_name      = Create_GDB      (GDB_file,DWG_name)
        csv_name       = GDB_file  + '\\' + DWG_name +'.csv'
        pdf_table      = GDB_file  + '\\' + DWG_name +'_DATA.pdf'
        pdf_MAP        = GDB_file  + '\\' + DWG_name +'_MAP.pdf'
        PDF            = GDB_file  + '\\' + DWG_name +'.pdf'

        if (str(python_version())) == '2.7.16':
            mxd_path   = Tamplates + '\\' + 'M1200_M1300.mxd'
        else:
            mxd_path   = Tamplates + '\\' + 'TEMP.aprx'
        gdb_path       = Tamplates + '\\' + 'temp.gdb'
        dwg_path       = GDB_file  + '\\' + DWG_name + '.dwg'

        # # #   Get M1200 and M1300 to a layer   # # #
        Polyline                = DWG + '\\' + 'Polyline'
        Filter                  = "\"Layer\" IN('M1200','M1300')"
        layer_name              = 'Line_M1200_M1300'
        layers_M1200_M1300      = Extract_dwg_to_layer   (fgdb_name,Polyline,layer_name,Filter)

        # # # Get Line Layer # # #
        Polyline                = DWG + '\\' + 'Polyline'
        layer_name              = 'Lines_all'
        Lines_all               = Extract_dwg_to_layer   (fgdb_name,Polyline,layer_name)

        # # #   Get all blocks and declaration   # # #
        Point                = DWG +'\\' + 'Point'
        layer_name2          = 'Blocks'
        Filter4              = "\"Entity\" = 'Insert'"
        layers_Block         = Extract_dwg_to_layer   (fgdb_name,Point,layer_name2,Filter4)

        declaration = fgdb_name + '\\' + 'declaration'
        try:
            arcpy.Select_analysis (layers_Block,declaration,"\"Layer\" in ('declaration','DECLARATION','Declaration')")
        except:
            layer_name2          = 'declaration'
            Filter5              = "\"Layer\" in ('declaration','DECLARATION','Declaration')"
            declaration         = Extract_dwg_to_layer   (fgdb_name,Point,layer_name2,Filter5)


        # # #   Get polygon M1200 and M1300, if not found, Create from Line   # # #
        polygon              = DWG +'\\' + 'Polygon'
        Filter3              = "\"Layer\" IN('M1200','M1300')"
        layer_name3          = "Poly_M1200_M1300"
        layers_Poly          = fgdb_name + '\\' + layer_name3
        try:
            arcpy.FeatureClassToFeatureClass_conversion( polygon, fgdb_name, layer_name3, Filter3)
            print ('Create FeatureClassToFeatureClass_conversion')
        except:
            print ('didnt Create FeatureClassToFeatureClass_conversion, trying creating polygon from line')
            # Create Polygon M1200
            poly_M1200   = 'in_memory' + '\\' + 'poly_M1200'
            Create_Polygon_From_Line         (layers_M1200_M1300 ,poly_M1200 ,"\"Layer\" = 'M1200'","'M1200'")
            Create_Polygon_From_Line         (layers_M1200_M1300,layers_Poly ,"\"Layer\" = 'M1300'","'M1300'")
            # Combine Polygons
            arcpy.Append_management          (poly_M1200,layers_Poly, "NO_TEST")

        # # #   Reading Files   # # #

        blocks   = Layer_Engine (layers_Block)
        delcar   = Layer_Engine (declaration        ,'all')
        lines_M  = Layer_Engine (layers_M1200_M1300 ,["Layer","Entity","LyrHandle","SHAPE@"])
        poly_M   = Layer_Engine (layers_Poly        ,'all')

        blocks.Extract_shape   ()
        delcar.Extract_shape   ()
        lines_M.Extract_shape  ()
        
        # # #  Action  # # #

        check_crs      = Check_coordinate_system(blocks,lines_M,poly_M)

        cheak_version  = cheak_cad_version (DWG)
        Check_decler   = cheak_declaration (delcar,lines_M)
        check_Blocks   = Check_Blocks      (blocks,Point,poly_M,lines_M,fgdb_name  )
        check_Lines    = Check_Lines       (lines_M,Lines_all,layers_Poly,fgdb_name)

        check_CADtoGeo   = Cheak_CADtoGeoDataBase (DWG,fgdb_name,blocks)
        check_annotation = Annotation_problems    (DWG,fgdb_name)

        data_csv = cheak_version + Check_decler + check_Blocks + check_Lines + check_CADtoGeo + check_annotation + check_crs

        Create_CSV                  (data_csv  ,csv_name)
        df = Creare_report_From_CSV (csv_errors,csv_name)
        Get_df_to_pdf               (df,pdf_table)
        Create_Pdfs                 (mxd_path,gdb_path,fgdb_name,pdf_MAP)
        MergaePdfs                  (pdf_MAP,pdf_table,PDF)

        os.remove (pdf_MAP)
        os.remove (pdf_table)

print_arcpy_message('#  #  #  #  #     F I N I S H     #  #  #  #  #')

