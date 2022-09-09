import geopandas as gpd
from pandas import read_sql
import json
from sqlalchemy import create_engine
from modules.config import Config
from modules.building_type_classification import building_type_level1_1994
import time

'''
This script reads buildings and grid from postgis,
transforms building geometries to centroids, adds
grid xyind attribute to them via spatial join and 
then finally sums building floor area grouping it 
by grid cell, building type and fuel and construction year.
The result is then pushed back to postgres (without geometry).

The final output of this script returns only those grid cells
which had buildings in their area. Other grid cells inside 
municipality borders are omitted. 
'''

# track time for completing the script
start_time = time.time()

# create config object for database and a connection
cfg = Config()
pg_connection = create_engine(cfg._db_connection_url())

# get co2data from posgres (note: no geometry field)
sql_co2data = "SELECT * FROM data.building_materials_gwp"
df_co2data = read_sql(sql_co2data, pg_connection)

# load material map per building type (json)
with open('datasets/building_type_material_mapping.json') as f:
   data = json.load(f)

# get buildings from postgres
sql_buildings = "SELECT * FROM data.buildings"
building_geom_col = 'geometry'
gdf_buildings = gpd.read_postgis(sql_buildings, pg_connection, geom_col=building_geom_col)  

# transform building geometries to centroid
gdf_buildings["geometry"] = gdf_buildings["geometry"].centroid

# get grid from postgres
sql_grid = "SELECT * FROM data.fi_grid_250m"
grid_geom_column = 'wkb_geometry'
gdf_grid = gpd.read_postgis(sql_grid, pg_connection, geom_col=grid_geom_column)

# limit grid to buildings extent using coordinate based index (reference: https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoDataFrame.cx.html)
bbox = gdf_buildings.total_bounds
gdf_grid = gdf_grid.cx[bbox[0]:bbox[2], bbox[1]:bbox[3]]

# before spatial join check that geodataframes are both in 3067
if not gdf_buildings.crs == "EPSG:3067" and gdf_grid.crs == "EPSG:3067":
    raise TypeError(f"One or both of buildings and grid was not in EPSG:3067. Buildings are in {gdf_buildings.crs} and grid in {gdf_grid.crs}.")

# spatial join xyind from grid to building centroids
gdf_buildings_xyind = gdf_buildings.sjoin(gdf_grid, how="left", predicate="within")

# drop columns which are not needed
gdf_buildings_xyind = gdf_buildings_xyind[['floor_area', 'fuel', 'building_type', 'year', 'geometry', 'xyind']]

# aggregate years to decades
gdf_buildings_xyind['decade'] = (gdf_buildings_xyind['year'] // 10) * 10

# aggregate building types to predefined categories
gdf_buildings_xyind['building_type'] = [building_type_level1_1994(x) for x in gdf_buildings_xyind['building_type']]

# create a new dataframe in which floor area is grouped by grid cell, decade, building type and fuel type
df_grouped_area_xyind = gdf_buildings_xyind.groupby(['xyind', 'decade', 'building_type', 'fuel'])['floor_area'].aggregate('sum').reset_index(name="floor_area_sum")

# In some cases the original data might have had 0 values for floor area so we delete them here
df_grouped_area_xyind = df_grouped_area_xyind.drop(df_grouped_area_xyind[df_grouped_area_xyind.floor_area_sum == 0].index)

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
type_list = df_grouped_area_xyind.building_type.unique()

# loop through the type list and for all rows in each type calculate co2 emissions
for i in type_list:
    df_grouped_area_xyind.loc[df_grouped_area_xyind.building_type==i, 'co2_emission'] = calc_material_co2(i) * df_grouped_area_xyind['floor_area_sum']

# group by xyind
df_total_co2 = df_grouped_area_xyind.groupby(['xyind'])['co2_emission'].aggregate('sum').reset_index(name="co2_total")

# join summed emissions back to grid, set non-paired cells to 0 value
gdf_final = gdf_grid.merge(df_total_co2, on='xyind', how='left').fillna({'co2_total':0}, downcast='infer')

# uncomment below if you want to send dataframe with aggregated building data by xyind to posgres for inspection
'''
engine = create_engine(cfg._db_connection_url("local_dev"))
df_grouped_area_xyind.to_sql("grid_with_aggregated_building_data",engine, schema="data",if_exists="replace", index_label="id")

with engine.connect() as con:
    con.execute('ALTER TABLE data.grid_with_aggregated_building_data ALTER "id" SET NOT NULL, ALTER "id" ADD GENERATED ALWAYS AS IDENTITY')
'''

# send final result to postgres
gdf_final.to_postgis(
    con=pg_connection,
    name="grid_with_building_materials_emission",
    schema="data",
    if_exists='replace',
)

# add identity field to the table
with pg_connection.connect() as con_pk:
    con_pk.execute('ALTER TABLE data.grid_with_building_materials_emission ADD COLUMN id int GENERATED BY DEFAULT AS IDENTITY')

# tell how long the script took to process
print(f"The script took {int((time.time()-start_time)//60)} minutes+ to run. Check result table in postgres.")