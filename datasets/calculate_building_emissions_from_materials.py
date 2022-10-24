import geopandas as gpd
import pandas as pd
import json
from sqlalchemy import create_engine
from modules.config import Config
from modules.building_type_mapper import grid_global_building_type_mapper_2018
from modules.building_year_mapper import year_mapper
from modules.building_fuel_mapper import fuel_mapper

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

# create config object for database and a connection
cfg = Config()
pg_connection = create_engine(cfg._db_connection_url())

# get co2data from postgres (note: no geometry field)
sql_co2data = "SELECT * FROM data.building_materials_gwp"
co2data = pd.read_sql(sql_co2data, pg_connection)

# load material map per building type
with open('datasets/building_type_material_mapping_grid_global.json') as f:
    building_type_material_map = json.load(f)

# get buildings from postgres
sql_buildings = "SELECT * FROM data.buildings"
building_geom_col = 'geometry'
buildings = gpd.read_postgis(sql_buildings, pg_connection, geom_col=building_geom_col)

# building type gets converted to float64, convert it back to nullable integer
buildings['building_type'] = buildings['building_type'].astype("Int64")

# transform building geometries to centroid
buildings["geometry"] = buildings["geometry"].centroid

# get grid from postgres
sql_grid = "SELECT * FROM data.fi_grid_250m"
grid_geom_column = 'wkb_geometry'
grid = gpd.read_postgis(sql_grid, pg_connection, geom_col=grid_geom_column)

# limit grid to buildings extent using coordinate based index
bbox = buildings.total_bounds
grid = grid.cx[bbox[0]:bbox[2], bbox[1]:bbox[3]]

# before spatial join check that geodataframes are both in 3067
if not (buildings.crs == "EPSG:3067" and grid.crs == "EPSG:3067"):
    raise TypeError(f"One or both of buildings and grid was not in EPSG:3067. Buildings are in {buildings.crs} and grid in {grid.crs}.")

# spatial join xyind from grid to building centroids
buildings_with_xyind = buildings.sjoin(grid, how="left", predicate="within")

# drop columns which are not needed
buildings_with_xyind = buildings_with_xyind[['floor_area', 'fuel', 'building_type', 'year', 'geometry', 'xyind']]

# Delete buildings that have 0 or null as value in floor area column
buildings_with_xyind = buildings_with_xyind.drop(buildings_with_xyind[(buildings_with_xyind.floor_area <= 0) | (buildings_with_xyind.floor_area.isna())].index)

# aggregate years to decades
buildings_with_xyind['decade'] = [year_mapper(x) for x in buildings_with_xyind['year']]

# aggregate building types to predefined categories
buildings_with_xyind['building_type_generalized'] = [grid_global_building_type_mapper_2018(x) for x in buildings_with_xyind['building_type']]

# Pass building fuels through fuel mapper module function
buildings_with_xyind_and_fuel = fuel_mapper(buildings_with_xyind, 'building_type', 'building_type_generalized', 'fuel')

# create a new dataframe in which floor area is grouped by grid cell, decade, building type and fuel type
floor_area_per_grid_cell = buildings_with_xyind_and_fuel.groupby(['xyind', 'decade', 'building_type_generalized', 'fuel'],dropna=False)['floor_area'].aggregate('sum').reset_index(name="floor_area_sum")

# function calculating total co2 emission for one square meter in specific building type
def calc_material_co2(type:str, mapping:dict):
    co2_per_m2 = 0.0
    # loop through json
    for key, value in mapping[type]["Materials_kg"].items():
        gwp_typical = 0.0
        # check if gwp_typical exists. Note that here it is assumed that key is integer in dataframe and string in json file. 
        if co2data.loc[(co2data['resourceid']==int(key)),'gwp_typical'].values.size > 0 :
            gwp_typical=co2data.loc[(co2data['resourceid']==int(key)),'gwp_typical'].values[0]
        co2_per_m2 += value * gwp_typical
    return co2_per_m2 

# get unique building types from the data
unique_building_types_in_data = floor_area_per_grid_cell.building_type_generalized.unique()

# loop through existing building types and for each one calculate total co2 emission per square meter
for i in unique_building_types_in_data:
    floor_area_per_grid_cell.loc[floor_area_per_grid_cell.building_type_generalized==i, 'co2_emission'] = calc_material_co2(i,building_type_material_map) * floor_area_per_grid_cell['floor_area_sum']

# group by xyind
total_co2_for_xyind = floor_area_per_grid_cell.groupby(['xyind'])['co2_emission'].aggregate('sum').reset_index(name="co2_total")

# join summed emissions back to grid, set non-paired cells to 0 value
final = grid.merge(total_co2_for_xyind, on='xyind', how='left').fillna({'co2_total':0}, downcast='infer')

# uncomment below if you want to send dataframe with aggregated building data by xyind to posgres for inspection
floor_area_per_grid_cell.to_sql("grid_with_aggregated_building_data",pg_connection, schema="data",if_exists="replace", index_label="id")
with pg_connection.connect() as con:
    con.execute('ALTER TABLE data.grid_with_aggregated_building_data ALTER "id" SET NOT NULL, ALTER "id" ADD GENERATED ALWAYS AS IDENTITY')

# send final result to postgres
final.to_postgis(
    con=pg_connection,
    name="grid_with_building_materials_emission",
    schema="data",
    if_exists='replace',
)

# add identity field to the table
with pg_connection.connect() as con_pk:
    con_pk.execute('ALTER TABLE data.grid_with_building_materials_emission ADD COLUMN id int GENERATED BY DEFAULT AS IDENTITY')
