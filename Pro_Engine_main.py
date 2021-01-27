# -*- coding: utf-8 -*-

import arcpy,math
import pandas as pd
import numpy as np
import uuid,json,datetime,sys,csv,os
from scipy.spatial import distance_matrix
from platform import python_version
arcpy.env.overwriteOutPut = True


class Layer_Engine():

    def __init__(self,layer,columns = 'all'):

        if columns == 'all':
            columns = [f.name.encode('UTF-8') for f in arcpy.ListFields(layer)]
            columns.extend(['SHAPE@AREA'])
            columns.extend(['SHAPE@'])

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

        self.data_shape,    self.df_shape , self.Not_closed = None, None, None
        self.exists_curves, self.bad_area   = None, None


    def Count_field(self,field):

        self.df['count'] = self.df.groupby(field)[field].transform('count')

    def Extract_shape(self):
        
        if self.shapetype != 'POINT':
            columns_shape            = [self.oid,'X','Y','Layer','Area','SHAPE']
            self.data_shape          = [[i[1],j.X,j.Y,i[2],i[3],i[0]] for i in arcpy.da.SearchCursor (self.layer,["SHAPE@",self.oid,'Layer','SHAPE@AREA']) for n in i[0] for j in n if j]
            self.df_shape            = pd.DataFrame(data = self.data_shape, columns = columns_shape)
            self.df_shape['index1']  = self.df_shape.index
            self.df_shape['X_Y']     = self.df_shape.apply(lambda row: Connect_rows(row['X'] , row['Y']),axis = 1)
        else:
            columns_shape            = [self.oid,'Layer','Entity','LyrHandle','X','Y']
            self.data_shape          = [[i[1],i[2],i[3],i[4],i[0].labelPoint.X,i[0].labelPoint.Y] for i in arcpy.da.SearchCursor (self.layer,["SHAPE@",self.oid,"Layer","Entity","LyrHandle"]) if i[0]]
            self.df_shape            = pd.DataFrame(data = self.data_shape, columns = columns_shape)
            self.df_shape['X_Y']     = self.df_shape.apply(lambda row: Connect_rows(row['X'] , row['Y']),axis = 1)

    def Filter_point_by_max_distance(self,X_Y,distance):

        if self.shapetype == 'POINT':
            if self.data_shape:
                point_data = [[item[4],item[5]] for item in self.data_shape]
                result     = Dis_2arrays_max(point_data,X_Y,distance,15)
                result     = [i[0] for i in result]
                df2        = self.df_shape.copy()
                df2        = df2[df2['X_Y'].isin(result)]
                return df2
            else:
                print ("Func Extract_shape wasnt activated")
        else:
            print ("Feature isn't POINT")


    def Len_field(self,field,as_int = False):

        if as_int:
            len_field = self.df[field].apply(str).apply(len).astype(int)
            if len_field.shape[0] > 1:
                len_field = len_field[0]
            return int(len_field)
        else:
            self.df[field + '_len'] = self.df[field].apply(len)

    def Filter_df(self,field,Value,Update_df = False):
        if Update_df:
            self.df = self.df[self.df[field] == Value]
        else:
            df_filter = self.df[self.df[field] == Value]
            return df_filter


    def Shape_closed(self):
        
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

        if self.shapetype == 'POLYGON':
            self.bad_area = [[i[4],i[3]] for i in self.data_shape if i[4] <= 0]
            if self.bad_area:
                return self.bad_area
        else:
            self.bad_area = False
            
    def Curves(self,Out_put):
        if self.shapetype in ['POLYGON','POLYLINE']:
            curves_list = [n for i in self.data for n in i if 'describe geometry object' in str(n) if 'curve' in str(json.loads(i[-1].JSON))]
            if curves_list:
                arcpy.CopyFeatures_management(curves_list,Out_put)
                self.exists_curves = True
                return len(curves_list)
            else:
                self.exists_curves = False

        return self.exists_curves

    def Check_Block_0_0(self):

        if self.shapetype == 'POINT':
            df2 = self.df_shape.copy()
            df2.where  ((df2["X"]==0) & (df2["Y"]==0) & (df2['Entity'] == "Insert"), inplace = True)
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
        
        exists_columns = set(self.df.columns[self.df.columns.str.contains(fields,na = False)])
        fields_in      = set(fields.split('|'))
        not_exists     = list(fields_in-exists_columns)
        return not_exists

    def Get_Field_Count_to_df(self,field,name_field_count = ''):

        if name_field_count == '':
            name_field_count = str(field) + "_num"
        count_data = self.df.groupby(field).size()
        count_data = count_data.to_frame().reset_index()
        count_data = self.df.merge(count_data, on=field).reset_index()
        count_data = count_data.rename(columns={0: name_field_count})
        return count_data

    
    def Dict(self,index_key):

        dict_  = self.df.set_index(index_key)
        dict_2 = dict_.T.to_dict()
        return dict_2

    def create_csv(self,out_put):
        out_put = out_put + '\\' + self.shapetype + '.csv'
        self.df.to_csv(out_put,encoding ='utf-8')

    def Groupby_and_count(self,field,name_field_count = ''):

        if name_field_count == '':
            name_field_count = str(field) + "_num"
        count_data = self.df.groupby(field).size()
        count_data = count_data.to_frame().reset_index()
        self.df = count_data


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
        declaration.append  ("E_Decleration_2","No Declaration Found")
    elif obj_declar.len_rows > 1:
        print_arcpy_message ("you have {} declarations, only 1 is approved".format(obj_declar.len_rows),2)
        declaration.append  (["E_Decleration_1","you have {} declarations, only 1 is approved".format(obj_declar.len_rows)])

    # check if distance to line is bigger then 100,000 meters
    distance = Check_distance_data_shape(obj_declar.data_shape,obj_line.data_shape)
    if distance > 100000:
        print_arcpy_message ("Decleration found to be far from M1300",2)
        declaration.append  (["E_Decleration_3","Decleration found to be far from M1300"])

    # check if missing values in: SURVEYOR, ACCURACY_HOR , ACCURACY_VER

    def missing_digi_in_field(df,field_name):
        declaration = []
        data = pd.to_numeric(df[field_name], errors='coerce').notnull().all()
        if not data:
            print_arcpy_message('field {} have no Value'.format(field_name),status = 2)
            declaration.append(['E_Decleration_4',str(field_name) + '  no value inside'])
        return declaration

    declaration = missing_digi_in_field(obj_declar.df,b"SURVEYOR")
    declaration = missing_digi_in_field(obj_declar.df,b"ACCURACY_VER")
    declaration = missing_digi_in_field(obj_declar.df,b"ACCURACY_HOR")

        
    # check if date is correct !!! why not extract from df??

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
            print_arcpy_message("layer 'declaration' missing fields: {}".format(''.join([i + '-' for i in missing_fields])[0:-1],status = 2))
            declaration.append(["E_Decleration_5","Missing fields"])
            declaration.append(["E_Decleration_5",missing_fields])

    return declaration


def Check_Blocks (obj_blocks,Point,Line_object):
    
    blocks     = []
    bad_charc     = ['-','"','.']
    cach_fields = [str(i.name) for i in arcpy.ListFields(Point) for n in i.name if n in bad_charc]
    if cach_fields:
        for letter in cach_fields:
            print_arcpy_message ("at block layers, there is bad Character ['-',' "" ','.'], letter: {}".format(letter),2)
            blocks.append       (["E_BLOCK_3","at block layers, there is bad Character ['-',' "" ','.'], letter: {}".format(letter)])


    # check if there is block in coordinate 0,0
    at_Zero_Zero = obj_blocks.Check_Block_0_0()
    if len(at_Zero_Zero) > 0:
        print_arcpy_message ('you have blocks at coordinates 0,0',2)
        blocks.append       (["E_BLOCK_2",'you have blocks at coordinates 0,0'])
        start = 0
        for i in at_Zero_Zero:
            blocks.append       ([str(start),'layer: {}, have blocks at coordinates 0,0'.format(i[1])])
            print_arcpy_message('block: {}'.format(str(i)),2)
            start += 1


    # Check if there is points with distance then more 100,000m from point
    x_y       = [[i[1],i[2]] for i in Line_object.data_shape]
    if x_y[0]:
        far_point = obj_blocks.Filter_point_by_max_distance([x_y[0]],100000)  # enough chacking 1 vertex of line to know if block is to far
        far_point = far_point[['Layer','Entity','X_Y']][((far_point['X'] != 0.0) | (far_point['Y'] != 0.0)) & (far_point['Entity'] == 'Insert')].values.tolist()
        if len(far_point) > 0:
            print_arcpy_message ('blocks outside the M1300 area',2)
            blocks.append       (["E_BLOCK_1",'blocks outside the M1300 area'])
            start_me = 0
            for i in far_point:
                blocks.append       ([str(start_me),'layer: {}, block name: {}, have coordinates at  {}'.format(i[0],i[1],i[2])])
                print_arcpy_message ('layer: {}, block name: {}, have coordinates at  {}'.format(i[0],i[1],i[2]),2)
                start_me += 1
        
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
        print_arcpy_message('Layer M1200 with bad geometry',2)
        lines.append       (["E_1200_3","Layer M1200 with bad geometry"])
        start_num = 0
        for i in close_pnt_m1200:
            print_arcpy_message ('M1200 vertxs = {}'.format(str(i)),2)
            lines.append        ([str(start_num),'M1200 vertxs = {}'.format(str(i))])
            start_num +=1

    if close_pnt_m1300:
        print_arcpy_message('Layer M1300 with bad geometry',2)
        lines.append       (["E_1300_3","Layer M1300 with bad geometry"])
        start_ = 0
        for i in close_pnt_m1300:
            print_arcpy_message  ('M1300 vertxs = {}'.format(str(i)))
            lines.append         ([str(start_),'M1300 vertxs = {}'.format(str(i))])
            start_ +=1


    # check Curves 
    obj_lines.Curves(obj_lines.layer + '_Curves')
    if obj_lines.exists_curves:
        print_arcpy_message('You have curves in layer M1200 or M1300')
        lines.append       (["E_Curves",'You have curves in layer M1200 or M1300'])

    # check more then 1 - M1200 or M1300
    only_1_layer = True
    M1200 = obj_lines.Filter_df('Layer','M1200')
    M1300 = obj_lines.Filter_df('Layer','M1300')
    if M1200.shape[0] > 1 or M1200.shape[0] == 0:
        print_arcpy_message("you have {} M1200,  1 is expected".format(str(M1200.shape[0])),2)
        lines.append       (["E_1200_2","you have {} M1200,  1 is expected".format(str(M1200.shape[0]))])
        only_1_layer = False
    if M1300.shape[0] > 1 or M1300.shape[0] == 0:
        print_arcpy_message("you have {} M1300,  1 is expected".format(str(M1300.shape[0])),2)
        lines.append       (["E_1300_2","you have {} M1300,  1 is expected".format(str(M1300.shape[0]))])
        only_1_layer = False

    # check if line are not closed
    if only_1_layer:
        obj_lines.Shape_closed()
        if obj_lines.Not_closed:
            print_arcpy_message ('there is vertexs that are not closed',2)
            lines.append        (['E_1200_4','there is vertexs that are not closed'])
            num_ = 1
            for i in obj_lines.Not_closed:
                print_arcpy_message ('vertx that is not closed: {}'.format(i),2)
                lines.append        ([str(num_),'vertx that is not closed: {}'.format(i)])
                num_ += 1

    return lines

def Create_CSV(data,csv_name):
    df        = pd.DataFrame(data,columns = ["Error Key", "Error"])
    df = df.set_index("Error Key")
    df.to_csv(csv_name)



def mxd_pdf_making(mxd_path,gdb_path,name,gdb,folder):

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

    pdf_output = add_endwith(pdf_output,endswith_ = '.pdf')

    p = arcpy.mp.ArcGISProject (mxd_path)
    p.updateConnectionProperties(gdb_Tamplate, gdb_path)

    # get 1 of the layers for zoom in
    m = p.listMaps('Map')[0]
    lyr = m.listLayers()[2]

    delete_templates = [m.removeLayer(i) for i in m.listLayers() if ('Tamplates' in i.dataSource)]

    lyt = p.listLayouts    ("Layout1")[0]
    mf  = lyt.listElements ('MAPFRAME_ELEMENT',"Map Frame")[0]
    mf.camera.setExtent    (mf.getLayerExtent(lyr,False,True))

    mf.exportToPDF(pdf_output)

def Cheak_CADtoGeoDataBase(DWG,fgdb_name):	
    # checking if arcpy can make layer to Geodatabase
	CADtoGeoDataBase = []
	try:
		arcpy.CADToGeodatabase_conversion(DWG,fgdb_name,'chacking',1)
		print_arcpy_message("tool made CAD to Geodatabase" , status = 1)
	except:
		print_arcpy_message("tool didnt made CAD to Geodatabase" , status = 0)
		CADtoGeoDataBase.append(["E_FC_1",'tool didnt made CAD to Geodatabase'])

    # check declaration in Geodatabase
	layer_cheacking = fgdb_name + '\\' + 'chacking\Point'
	decl_list = [row[0] for row in arcpy.da.SearchCursor(layer_cheacking,["Layer"]) if row[0] in ('declaration','DECLARATION')]
	if len(decl_list) > 1 or len(decl_list) == 0:
		massage = "layer declaration from chacking\point (Geodatabase) found {} declaration, must be 1 ".format(len(decl_list))
		print_arcpy_message(massage, status = 2)
		CADtoGeoDataBase.append(["E_Decleration_8",massage])

	return CADtoGeoDataBase

def get_crazy_long_test(DWG):
		long_prob = []
		anno  = DWG +'\\' + 'Annotation'
		x = [[row[0],row[1],row[2],row[3]] for row in arcpy.da.SearchCursor (anno,['Layer','TxtMemo','Entity','RefName'])]
		for i in x:
			if (len(i[1]) > 254) or (len(i[2]) > 254) or (len(i[3]) > 254):
				print_arcpy_message("{} is with more then 254 characters, plz notice".format(str(i[0])),status = 2)
				long_prob.append   (["E_Annotation","{} is with more then 254 characters".format(i[0])])
				
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
        save_name   = path_result
        path        = pd.read_csv(path,encoding="ISO-8859-8")
        path        = path.set_index("Error_ID")

        path_result = pd.read_csv(path_result,encoding="ISO-8859-8")
        path_result = path_result.set_index("Error Key")
        path_result = path_result.drop(['Error'], axis=1)

        result      = pd.concat([path, path_result], axis=1, join="inner")
        path,name   = os.path.split(save_name)
        new_csv     = path + '\\' + name.split('.')[0] + '_report.csv'

        result.to_csv(new_csv,encoding="ISO-8859-8")

        if del_extra_report:
            os.remove(save_name)

print_arcpy_message('#  #  #  #  #     S T A R T     #  #  #  #  #')

# # # In Put # # #
DWGS        = [r"C:\Users\Administrator\Desktop\medad\python\Work\Engine_Cad_To_Gis\DWG\dimona_366A_4.dwg"]
# DWGS        = arcpy.GetParameterAsText(0).split(';')
csv_errors  = r"C:\Users\Administrator\Desktop\medad\python\Work\Engine_Cad_To_Gis\Errors_Check_DWG.csv"

# # #     Preper Data    # # #
scriptPath     = os.path.abspath (__file__)
folder_basic   = os.path.dirname (scriptPath)
Tamplates      = folder_basic + "\\" + "Tamplates"
GDB_file       = folder_basic + "\\" + "Temp"

for DWG in DWGS:
    print_arcpy_message (DWG,1)
    DWG_name       = os.path.basename(DWG).split(".")[0]
    fgdb_name      = Create_GDB      (GDB_file,DWG_name)
    csv_name       = GDB_file  + '\\' + DWG_name +'.csv'
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


    # # #   Get all blocks and declaration   # # #
    Point                = DWG +'\\' + 'Point'
    layer_name2          = 'Blocks'
    layers_Block         = Extract_dwg_to_layer   (fgdb_name,Point,layer_name2)

    declaration = fgdb_name + '\\' + 'declaration'
    arcpy.Select_analysis (layers_Block,declaration,"\"Layer\" in ('declaration','DECLARATION','Declaration')")


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
    poly_M   = Layer_Engine (layers_Poly ,'all')

    blocks.Extract_shape   ()
    delcar.Extract_shape   ()
    lines_M.Extract_shape  ()
    

    # # #  Action  # # #

    cheak_version  = cheak_cad_version (DWG)
    Create_CSV      (cheak_version,csv_name)
    Check_decler   = cheak_declaration (delcar,lines_M)
    check_Blocks   = Check_Blocks      (blocks,Point,lines_M)
    check_Lines    = Check_Lines       (lines_M)

    check_CADtoGeo   = Cheak_CADtoGeoDataBase(DWG,fgdb_name)
    check_annotation = get_crazy_long_test (DWG)

    data_csv = cheak_version + Check_decler + check_Blocks + check_Lines + check_CADtoGeo + check_annotation

    Create_CSV             (data_csv,csv_name)
    Creare_report_From_CSV (csv_errors,csv_name,del_extra_report = True)

    Create_Pdfs  (mxd_path,gdb_path,fgdb_name,GDB_file +'\\' +DWG_name + '.pdf' )

print_arcpy_message('#  #  #  #  #     F I N I S H     #  #  #  #  #')





