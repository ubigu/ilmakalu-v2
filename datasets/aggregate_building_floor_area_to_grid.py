import geopandas as gpd
from pandas import read_sql
import json
from sqlalchemy import create_engine
from modules.config import Config
from modules.building_type_classification import building_type_level1_1994
import time
#import matplotlib.pyplot as plt <-- uncomment if you want to visualize dataframe for testing

'''
This script reads buildings and grid from postgis,
transforms building geometries to centroids, adds
grid xyind attribute to them via spatial join and 
then finally sums building floor area grouping it 
by grid cell, building type and fuel and construction year.
The result is then pushed back to postgres (without geometry).
'''

# track time for completing the script
start_time = time.time()

# create config object for database
cfg = Config()

# create connection to postgres
engine = create_engine(cfg._db_connection_url("local_dev"))

# establish connection string
db_connection_url = cfg._db_connection_url("local_dev")
con = create_engine(db_connection_url) 

# get co2data from posgres (note: no geometry field)
sql_co2data = "SELECT * FROM data.co2data_building_materials"
df_co2data = read_sql(sql_co2data, con)

# load material map per building type (json)
with open('datasets/materials_per_building.json') as f:
   data = json.load(f)

# get buildings from postgres
sql_buildings = "SELECT * FROM data.rakennukset"
building_geom_col = 'geometry'
df_buildings = gpd.read_postgis(sql_buildings, con, geom_col=building_geom_col)  

# transform building geometries to centroid
df_buildings["geometry"] = df_buildings["geometry"].centroid

# get grid from postgres
sql_grid = "SELECT * FROM data.fi_grid_250m"
grid_geom_column = 'wkb_geometry'
df_grid = gpd.read_postgis(sql_grid, con, geom_col=grid_geom_column)

# limit grid to buildings extent using coordinate based index (reference: https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoDataFrame.cx.html)
bbox = df_buildings.total_bounds
df_grid = df_grid.cx[bbox[0]:bbox[2], bbox[1]:bbox[3]]

# spatial join xyind from grid to building centroids
df_buildings_with_xyind = df_buildings.sjoin(df_grid, how="left", predicate="within")
df_buildings_with_xyind = df_buildings_with_xyind[[cfg.floor_area_attribute(), cfg.fuel_attribute(), cfg.building_code_attribute(), cfg.year_attribute(),"geometry","xyind"]]

# aggregate years to decades by using ((x//10)*10) trick with list comprehension
df_buildings_with_xyind[cfg.year_attribute()] = [((x//10)*10) for x in df_buildings_with_xyind[cfg.year_attribute()]]

# aggregate building types to predefined categories
df_buildings_with_xyind[cfg.building_code_attribute()] = [building_type_level1_1994(x) for x in df_buildings_with_xyind[cfg.building_code_attribute()]]

# create a new dataframe in which floor area is grouped by grid cell, decade, building type and fuel type
df_bu_grouped = df_buildings_with_xyind.groupby(['xyind',cfg.year_attribute(), cfg.building_code_attribute(), cfg.fuel_attribute()])[cfg.floor_area_attribute()].aggregate('sum').reset_index(name="floor_area_sum")

# rename columns
df_bu_grouped = df_bu_grouped.rename(columns={cfg.year_attribute():"decade",cfg.building_code_attribute():"building_type",cfg.fuel_attribute():"fuel"})

# add 1 to index so that it won't start from 0
df_bu_grouped.index += 1

# In some cases the original data might have had 0 values for floor area so we delete them here
df_bu_grouped = df_bu_grouped.drop(df_bu_grouped[df_bu_grouped.floor_area_sum == 0].index)

# function calculating total co2 emission for one square meter in specific building type
def calc_material_co2(type:str):
    co2_emission_m2 = 0.0
    # loop through json
    for key, value in data[type]["Materials_kg"].items():
        gwp_typicalValue =0.0
        # check if gwp_typical exists. Note that here is assumed that key is integer in dataframe and string in json file. 
        if df_co2data.loc[(df_co2data['resourceid']==int(key)),'gwp_typical'].values.size > 0 :
            gwp_typicalValue=df_co2data.loc[(df_co2data['resourceid']==int(key)),'gwp_typical'].values[0]
        co2_emission_m2 += value * gwp_typicalValue
    return co2_emission_m2 

# get unique building types
type_list = df_bu_grouped.building_type.unique()

# loop through the type list and for all rows in each type calculate co2 emissions
for i in type_list:
    df_bu_grouped.loc[df_bu_grouped.building_type==i, 'co2_emission'] = calc_material_co2(i) * df_bu_grouped['floor_area_sum']

# group by xyind

# get geometry back on or go back and keep it along

# push result back to postgis
engine = create_engine(cfg._db_connection_url("local_dev"))
df_bu_grouped.to_sql("grid_with_agg_floor_area",engine, schema="data",if_exists="replace", index_label="id")

# set id field as identity in postgres
with engine.connect() as con_pk:
    con_pk.execute('ALTER TABLE data.grid_with_agg_floor_area ALTER "id" SET NOT NULL, ALTER "id" ADD GENERATED ALWAYS AS IDENTITY')


# matplotlib script for checking the result?

print(f"The script took {(time.time()-start_time)//60} minutes+ to run")