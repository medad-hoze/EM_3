import arcpy,os

def add_field(fc,field,Type = 'TEXT'):
    try:
        TYPE = [i.name for i in arcpy.ListFields(fc) if i.name == field]
        if not TYPE:
            print (fc)
            print (field)
            print(Type)
            arcpy.AddField_management (fc, field, Type, "", "", 500)
    except:
        pass


def Put_all_fields_in_all_layers(path):

    arcpy.env.workspace = path
    list_fcs = [path + '\\' +  str(i) for i in arcpy.ListFeatureClasses() if i]

    fields        = []
    alread_exists = []
    error_fields  = ['OBJECTID','OID','Shape']

    for i in list_fcs:
        for n in arcpy.ListFields(i):
            if n.name not in alread_exists and n.name not in error_fields:
                fields.append([n.name,n.type])
                alread_exists.append(n.name)

    exe = [add_field(lyr,i[0],i[1]) for lyr in list_fcs for i in fields]



def Get_dataset_to_DWG_fix(dataset_path,out_dwg,dwg):

    dect_ver     = {'2000':"DWG_R2000", '2004':"DWG_R2004", '2005':"DWG_R2005", '2007':"DWG_R2007", '2010':"DWG_R2010"}
    dwg_ver      = '2004'

    line       = dataset_path + '\\' + 'Polyline'
    point      = dataset_path + '\\' + 'Point'
    Annotation = dataset_path + '\\' + 'Annotation'

    list_poly_line_anno = [line,Annotation]

    exp_frozen  =  "change_to_zero            (!LyrFrzn!)"
    exp_vis     =  "change_zero_to_minus      (!BlkColor!)"
    exp_LineWt  =  "Minus_1_to_zero           (!BlkLineWt!)"
    exp_lyrOn   =  "zero_to_one               (!LyrOn!)"
    redouceX    =  "reduce_insert_line        (!ScaleZ!)"
    redouceY    =  "reduce_insert_line        (!ScaleY!)"
    redouceZ    =  "reduce_insert_line        (!ScaleX!)"

    change_to_zero = """def change_to_zero(num):
        if num == 1:
            return 0
        else:
            return num"""

    change_zero_to_minus = """def change_zero_to_minus(num):
        if num == 0:
            return -1
        else:
            return num"""

    Minus_1_to_zero = """def Minus_1_to_zero(num):
        if num == -1:
            return 0
        else:
            return num""" 

    zero_to_one = """def zero_to_one(num):
        if num == 1:
            return 0
        return num"""

    reduce_insert_line = """def reduce_insert_line(x):
        return 0.01"""
        

    arcpy.CalculateField_management (point,"LyrFrzn"  ,exp_frozen,"PYTHON",change_to_zero      )
    arcpy.CalculateField_management (point,"BlkColor" ,exp_vis   ,"PYTHON",change_zero_to_minus)
    arcpy.CalculateField_management (point,"BlkLineWt",exp_LineWt,"PYTHON",Minus_1_to_zero     )

    arcpy.CalculateField_management (point,"ScaleZ",redouceZ,"PYTHON",reduce_insert_line     )
    arcpy.CalculateField_management (point,"ScaleY",redouceY,"PYTHON",reduce_insert_line     )
    arcpy.CalculateField_management (point,"ScaleX",redouceX,"PYTHON",reduce_insert_line     )

    arcpy.CalculateField_management (Annotation,"LyrOn",exp_lyrOn,"PYTHON",zero_to_one       )


    for lyr in list_poly_line_anno:
        name = os.path.basename(lyr)
        arcpy.MakeFeatureLayer_management       (lyr,name)
        arcpy.SelectLayerByAttribute_management (name,"ADD_TO_SELECTION","\"Entity\" = 'Insert'")
        arcpy.DeleteFeatures_management         (name)
        # if lyr == line:
        #     arcpy.DeleteField_management(lyr,"Entity")

    list_fcs = list_poly_line_anno + [point]
    Put_all_fields_in_all_layers(dataset_path)
    arcpy.ExportCAD_conversion(list_fcs,dect_ver[str(dwg_ver)],out_dwg,"Ignore_Filenames_in_Tables", "OVERWRITE_EXISTING_FILES")


dataset_path = r'C:\Users\Administrator\Desktop\medad\python\Work\Engine_Cad_To_Gis\Temp\150asMade_1.gdb\chacking'
out_dwg      = r'C:\Users\Administrator\Desktop\medad\python\Work\Engine_Cad_To_Gis\Temp\150asMade.dwg'
dwg_source   = r"C:\Users\Administrator\Desktop\medad\python\Work\Engine_Cad_To_Gis\150asMade.dwg"


Get_dataset_to_DWG_fix(dataset_path,out_dwg,dwg_source)


