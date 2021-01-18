import pandas as pd

def read_excel_to_json(path2,out_put):
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
            print "coudent read sheet {}".format(name)
        df = df.append(sheet,ignore_index = True)
    
    json = df.to_json(out_put)
    return json


path2   = r"C:\Users\medad\python\GIStools\Work Tools\Engine_Cad_To_Gis\DATA_DIC_20200218-MAVAAT.xlsx"
out_put = r'C:\Users\medad\python\GIStools\Work Tools\Engine_Cad_To_Gis\Json_try.json'
read_excel_to_json(path2,out_put)
