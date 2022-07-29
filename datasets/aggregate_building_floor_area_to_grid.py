import geopandas as gpd
from sqlalchemy import create_engine
from modules.config import Config
from modules.building_type_classification import building_type_level1_1994
#import matplotlib.pyplot as plt <-- uncomment if you want to visualize dataframe for testing

'''
This script reads buildings and grid from postgis,
transforms building geometries to centroids, adds
grid xyind attribute to them via spatial join and 
then finally sums building floor area grouping it 
by grid cell, building type and fuel and construction year.
The result is then pushed back to postgres (without geometry).
'''

# create config object for database
cfg = Config()

# create connection to postgres
engine = create_engine(cfg._db_connection_url("local_dev"))

# establish connection string
db_connection_url = cfg._db_connection_url("local_dev")
con = create_engine(db_connection_url) 

# get buildings from postgis
sql_buildings = "SELECT * FROM data.rakennukset LIMIT 10"
#WHERE id = 33000 OR ID = 33002 OR ID = 11328
building_geom_col = 'geometry'
df_buildings = gpd.read_postgis(sql_buildings, con, geom_col=building_geom_col)  
#print(data_buildings.head())

# transform building geometries to centroid
df_buildings["geometry"] = df_buildings["geometry"].centroid

# get grid from postgis
sql_grid = "SELECT * FROM data.fi_grid_250m WHERE xyind = '3663756679375' OR xyind = '3733756685375' OR xyind = '3666256673875' OR xyind = '3763756680375' OR xyind = '3668756673375'"
grid_geom_column = 'wkb_geometry'
df_grid = gpd.read_postgis(sql_grid, con, geom_col=grid_geom_column)

# spatial join xyind from grid to building centroids
df_buildings_with_xyind = df_buildings.sjoin(df_grid, how="left", predicate="within")
df_buildings_with_xyind = df_buildings_with_xyind[[cfg.floor_area_attribute(), cfg.fuel_attribute(), cfg.building_code_attribute(), cfg.year_attribute(),"geometry","xyind"]]

# aggregate years to decades by using ((x//10)*10) trick with list comprehension
df_buildings_with_xyind[cfg.year_attribute()] = [((x//10)*10) for x in df_buildings_with_xyind[cfg.year_attribute()]]

# aggregate building types to predefined categories
df_buildings_with_xyind[cfg.building_code_attribute()] = [building_type_level1_1994(x) for x in df_buildings_with_xyind[cfg.building_code_attribute()]]

# create a new dataframe in which floor area is grouped by grid cell, decade, building type and fuel type
df_grid_with_agg_floor_area = df_buildings_with_xyind.groupby(['xyind',cfg.year_attribute(), cfg.building_code_attribute(), cfg.fuel_attribute()])[cfg.floor_area_attribute()].aggregate('sum').reset_index(name="floor_area_sum")

# rename columns
df_grid_with_agg_floor_area = df_grid_with_agg_floor_area.rename(columns={cfg.year_attribute():"decade",cfg.building_code_attribute():"building_type",cfg.fuel_attribute():"fuel"})

# add 1 to index so that it won't start from 0
df_grid_with_agg_floor_area.index += 1

# push result back to postgis
engine = create_engine(cfg._db_connection_url("local_dev"))
df_grid_with_agg_floor_area.to_sql("grid_with_agg_floor_area",engine, schema="data",if_exists="replace", index_label="id")

# set id field as identity in postgres
with engine.connect() as con_pk:
    con_pk.execute('ALTER TABLE data.grid_with_agg_floor_area ALTER "id" SET NOT NULL, ALTER "id" ADD GENERATED ALWAYS AS IDENTITY')
