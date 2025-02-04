import os
import shutil
import datetime
import zipfile
import pandas as pd
import geopandas as gpd
from prefect import flow, task

JSON_DIR = "/sciclone/geounder/dev/geoBoundaries/scripts/geoBoundaryBot/external/AuthData/Geojsons/"  #PATH TO THE GEJSON FILES
CSV_DIR = "/sciclone/geounder/dev/geoBoundaries/scripts/geoBoundaryBot/external/AuthData/GeoJson.csv"
DATA_DIR = "/sciclone/geounder/dev/geoBoundaries/scripts/geoBoundaryBot/external/AuthData/Data/"
SOURCE_DIR = "/sciclone/geounder/dev/geoBoundaries/scripts/geoBoundaryBot/external/AuthData/sourceData/"

# @flow(name='UNSALB',flow_run_name="{file_name}",log_prints=True)
#Method to zip the files 
def zip_directory(path, zip_path, file_name):

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, arcname=file)
    print(f"Successfully zipped {path} to {zip_path}")

def create_directory(text, iso, outputFile_path, file_name, admLevel):
    filename=iso
    filePath=os.path.join(DATA_DIR,filename)
    os.makedirs(filePath,exist_ok=True)
    admFilePath=os.path.join(filePath,admLevel)
    os.makedirs(admFilePath,exist_ok=True)
    if os.path.isdir(admFilePath):
        shutil.copy2(outputFile_path, admFilePath)
    meta_path = os.path.join(admFilePath,"meta.txt")
    with open(meta_path, "w") as f:
        f.write(text)
    zip_path = os.path.join(SOURCE_DIR,filename+"_"+admLevel+".zip")
    zip_directory(admFilePath,zip_path, file_name)
        


def create_meta_file(fileName, admLevel):
 
    file = fileName
    with open(CSV_DIR, 'r') as file:
        lines = file.readlines()
    
    data = []
    for line in lines:
        fields = line.strip().split(',')
        # Process fields as needed (e.g., combine or split)
        data.append(fields)
    metaData = pd.DataFrame(data, columns=["name", "iso", "date", "source1","source","sourceLink","column1","column2"])
    # print(metaData)

    # Iterate through each row in the DataFrame
    for index, row in metaData.iterrows():
        # Check if the condition in the "name" column is met
        if row["name"] == fileName:
            # Extract values from the row and assign them to variables
            file = row["name"]
            isoCode = row["iso"]
            boundary=row["date"]
            source1=row["source1"]
            source1=source1.replace('"','')
            source = row["source"]
            boundary=boundary.replace("(", "").replace(")", "")
            iso=isoCode.upper()
            boundary=boundary.lstrip()
            original_string = boundary
 
            start_date, _, end_date = original_string.split()
            start_year, start_month, start_day = start_date.split("-")
            end_year, end_month, end_day = end_date.split("-")
            if start_day == "00" or start_month == "00":
                new_date = f"01-01-{start_year} to {end_day}-{end_month}-{end_year}"
            else:
                new_date = f"{start_day}-{start_month}-{start_year} to {end_day}-{end_month}-{end_year}"

            text = f"Boundary Representative of Year: {new_date}\n" \
            f"ISO-3166-1 (Alpha-3): {isoCode.upper()}\n" \
            f"Boundary Type: {admLevel}\n" \
            f"Canonical Boundary Type Name: { file if admLevel == 'ADM0' else ''}\n" \
            f"Source 1: {source1}\n" \
            f"Source 2: UNSALB\n" \
            f"Release Type: gbAuthoritative \n" \
            f"License: UN SALB Data License \n" \
            f"License Notes:\n" \
            f"License Source: https://github.com/wmgeolab/geoBoundaryBot/blob/main/dta/licenseText/SALB_DataSpecifications_v2.0.pdf \n" \
            f"Link to Source Data: {source if 'https' in source else 'https://salb.un.org/en/data/'+isoCode } \n" \
            f"Other Notes:  \n"

    return text, iso

@task
def process_geojson_files(directory, dissolve_column, shape_type, adm_level):
    geojson_files = [file for file in os.listdir(directory) if file.endswith('.geojson')]
    for geojson_file in geojson_files:
        file_name = geojson_file.split(".")[0]
        input_file_path = os.path.join(directory, geojson_file)
        # Check if the filename is "South Africa" and skip processing if it is
        if file_name == "South Africa":
            print(f"Skipping file '{geojson_file}' as it is named 'South Africa'")
            continue
        gdf = gpd.read_file(input_file_path)

        # Apply dissolve method
        if dissolve_column:
            if adm_level == "ADM0":
                possible_dissolve_columns = ["cty_nm", "ct_nm", "iso3cd"]
                for possible_column in possible_dissolve_columns:
                    if possible_column in gdf.columns:
                        dissolve_column = possible_column
                        break
            
            else:
                dissolve_column = "adm1nm"

            gdf = gdf.dissolve(by=dissolve_column, as_index=False)
            # Save the updated GeoDataFrame back to the file
            # output_dir = os.path.join(directory, adm_level, f"{file_name}_{adm_level}.geojson")
            # gdf.to_file(output_dir, driver='GeoJSON')

            # gdf = gpd.read_file(output_dir)

        if adm_level == "ADM2":
            # Rename the columns as needed
            new_column_names = {
                "iso3cd": "shapeGroup",
                "adm2nm": "shapeName",
                # Add more column name mappings as needed
            }
        elif adm_level == "ADM1":
            new_column_names = {
                "iso3cd": "shapeGroup",
                dissolve_column: "shapeName",
                # Add more column name mappings as needed
            }
        else:
            # Rename the columns as needed
            if dissolve_column == "iso3cd":
                new_column_names = {
                "iso3cd": "shapeGroup",
                # dissolve_column: "shapeName",
                # Add more column name mappings as needed
            }
                gdf["shapeName"] = file_name
            else:
                new_column_names = {
                    "iso3cd": "shapeGroup",
                    dissolve_column: "shapeName",
                    # Add more column name mappings as needed
                }
        gdf.rename(columns=new_column_names, inplace=True)
        # Add a new column with the provided values
        gdf["shapeType"] = shape_type

        # Columns you want to keep
        remove_columns = ["CYP", "LSO", "ROU"]
        if gdf["shapeGroup"].isin(remove_columns).any() and adm_level == "ADM2":
            columns_to_keep = ["shapeGroup", "shapeType", "geometry"]
        else:
            columns_to_keep = ["shapeGroup", "shapeName", "shapeType", "geometry"]

        # Drop columns except the ones in columns_to_keep
        columns_to_drop = [col for col in gdf.columns if col not in columns_to_keep]   
        gdf.drop(columns_to_drop, axis=1, inplace=True)

        # Save the updated GeoDataFrame back to the file
        output_dir = os.path.join(directory, adm_level, f"{file_name}_{adm_level}.geojson")
        gdf.to_file(output_dir, driver='GeoJSON')

        #printing the column names
        print("The column names of data frame :",gdf.columns)

        text, iso = create_meta_file(file_name, admLevel=adm_level)
        create_directory(text, iso, output_dir, file_name, admLevel=adm_level)

def create_adm2level_geojsons(directory):
    print("ADM2 FILES")
    process_geojson_files(directory, dissolve_column=None, shape_type="ADM2", adm_level="ADM2")

def create_adm1level_geojsons(directory):
    print("ADM1 FILES")
    process_geojson_files(directory, dissolve_column="adm1nm", shape_type="ADM1", adm_level="ADM1")

def create_adm0level_geojsons(directory):
    print("ADM0 FILES")
    process_geojson_files(directory, dissolve_column="adm0", shape_type="ADM0", adm_level="ADM0")


def generate_flow_run_name():
    date = datetime.datetime.now(datetime.timezone.utc)

    return f"On-{date:%A}-{date:%B}-{date.day}-{date.year}"

@flow(name='UNSALB: Generating Zip Files',flow_run_name=generate_flow_run_name,log_prints=True)
def generate_geojsons(directory):
    create_adm2level_geojsons(directory)
    create_adm1level_geojsons(directory)
    create_adm0level_geojsons(directory)

generate_geojsons(JSON_DIR)
 
