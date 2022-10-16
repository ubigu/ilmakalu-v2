import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine
from modules.config import Config
from modules.building_type_mapper import grid_global_building_type_mapper_2018
from modules.building_year_mapper import year_mapper
from modules.building_fuel_mapper import fuel_mapper
from modules.building_counter_for_grid_cells import building_counter_for_grid_cells

'''
This script calculates building counts and area
for existing building types grouped by a grid cell. 
Result is pushed to Postgres to act as a source dataset
for later processing. 
'''

# Create config object for database and a connection
cfg = Config()
pg_connection = create_engine(cfg._db_connection_url())

# Get buildings from postgres
sql_buildings = "SELECT * FROM data.buildings"
building_geom_col = 'geometry'
buildings = gpd.read_postgis(sql_buildings, pg_connection, geom_col=building_geom_col)

# Building type gets converted to float64, convert it back to nullable integer
buildings['building_type'] = buildings['building_type'].astype("Int64")

# Building year gets converted to float64, convert it back to nullable integer
buildings['year'] = buildings['year'].astype("Int64")

# Delete buildings that have 0 or null as value in floor area column
buildings = buildings.drop(buildings[(buildings.floor_area <= 0) | (buildings.floor_area.isna())].index)

# Transform building geometries to centroid
buildings["geometry"] = buildings["geometry"].centroid

# Get grid from postgres
sql_grid = "SELECT * FROM data.fi_grid_250m"
grid_geom_column = 'wkb_geometry'
grid = gpd.read_postgis(sql_grid, pg_connection, geom_col=grid_geom_column)

# Limit grid to buildings extent using coordinate based index
bbox = buildings.total_bounds
grid = grid.cx[bbox[0]:bbox[2], bbox[1]:bbox[3]]

# Before spatial join check that geodataframes are both in 3067
if not buildings.crs == "EPSG:3067" and grid.crs == "EPSG:3067":
    raise TypeError(f"One or both of buildings and grid was not in EPSG:3067. Buildings are in {buildings.crs} and grid in {grid.crs}.")

# Spatial join xyind from grid to building centroids
buildings_with_xyind = buildings.sjoin(grid, how="left", predicate="within")

# Drop columns which are not needed
buildings_with_xyind = buildings_with_xyind[['floor_area', 'fuel', 'building_type', 'year', 'geometry', 'xyind']]

# Generalize building types according to 2018 classification. A spesific function that allows certain 2nd and 3rd level hierarchies is utilized. 
buildings_with_xyind['building_type_generalized'] = [grid_global_building_type_mapper_2018(x) for x in buildings_with_xyind['building_type']]

# Pass building construction years through year mapper module function
buildings_with_xyind['decade'] = [year_mapper(x) for x in buildings_with_xyind['year']]

# Pass building fuels through fuel mapper module function
buildings_with_xyind_and_fuel = fuel_mapper(buildings_with_xyind, 'building_type', 'building_type_generalized', 'fuel').copy()

# Calculate building counts and floor area sums per grid cell
buildings_with_xyind_and_fuel_and_counts = building_counter_for_grid_cells(buildings_with_xyind_and_fuel,"xyind","fuel","decade","floor_area","building_type_generalized").copy()

# rename columns to match data schema that later processing requires
final_no_geom = buildings_with_xyind_and_fuel_and_counts.rename(columns={"decade":"rakv","fuel":"energiam","geometry":"geom"})

# create final geodataframe and hand it centroid geometry from grid
grid["wkb_geometry"] = grid["wkb_geometry"].centroid
final = gpd.GeoDataFrame(pd.merge(final_no_geom,grid[["xyind","wkb_geometry"]], on="xyind", how="left"), crs="EPSG:3067", geometry="wkb_geometry")
final = final.rename(columns={"wkb_geometry":"geometry"})

# send the result to postgis
final.to_postgis(
    con=pg_connection,
    name="buildings_grid_global",
    schema="data",
    if_exists='replace',
)