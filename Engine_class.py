# -*- coding: utf-8 -*-

from Basic_Tools import *

import arcpy,math
import pandas as pd
import numpy as np
import uuid,json,datetime,sys,csv,os
from scipy.spatial import distance_matrix

arcpy.env.overwriteOutPut = True


class Layer_Engine():

    def __init__(self,layer,columns = 'all'):

        if columns == 'all':
            columns = [str(f.name.encode('UTF-8')) for f in arcpy.ListFields(layer)]
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

        exists_columns = set(self.df.columns[self.df.columns.str.contains(fields)])
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


class Layer_Management():

    def __init__(self,Layer):
        if arcpy.Exists(Layer):
            self.gdb          = os.path.dirname  (Layer)
            self.name         = os.path.basename (Layer)
            self.layer        = Layer
            self.desc         = arcpy.Describe(layer)
            self.oid          = str(self.desc.OIDFieldName)
            self.sr           = self.desc.spatialReference
            self.Geom_type    = ShapeType(self.desc)

        else:
            print_arcpy_message ("Layer is not exist")
            pass

    def fields(self):
        return [str(f.name) for f in arcpy.ListFields(self.layer)]

    def Get_Label_Point_As_Point(self,out_put):

        arcpy.CopyFeatures_management([arcpy.PointGeometry(i.shape.labelPoint) for i in arcpy.SearchCursor (self.layer) if i.shape],out_put)
        return out_put

    def Multi_to_single(self):
    
        multi = False
        len_before = int(str(arcpy.GetCount_management(self.layer)))
        temp_lyer = self.layer  + 'Temp'
        save_name = self.layer
        arcpy.MultipartToSinglepart_management (self.layer,temp_lyer)
        arcpy.Delete_management                (self.layer)
        arcpy.Rename_management                (temp_lyer,save_name)
        len_after = int(str(arcpy.GetCount_management(self.layer)))
        if len_after > len_before:
            multi = True

        return multi
