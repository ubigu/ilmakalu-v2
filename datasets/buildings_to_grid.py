from ntpath import join
import geopandas as gpd
from requests import Request
from owslib.wfs import WebFeatureService
from sqlalchemy import create_engine
from modules.config import Config
import matplotlib.pyplot as plt
from shapely.geometry.polygon import Polygon
from shapely.geometry.multipolygon import MultiPolygon

# create config object for database
cfg_test = Config()

# create connection to postgres
engine = create_engine(cfg_test._db_connection_url("local_dev"))

# establish connection string
db_connection_url = cfg_test._db_connection_url("local_dev")
con = create_engine(db_connection_url) 

# get buildings from postgis
sql_buildings = "SELECT * FROM data.rakennukset LIMIT 10"
#WHERE id = 33000 OR ID = 33002 OR ID = 11328
building_geom_col = 'geometry'
data_buildings = gpd.read_postgis(sql_buildings, con, geom_col=building_geom_col)  
#print(data_buildings.head())

# transform building geometries to centroid
data_buildings["geometry"] = data_buildings["geometry"].centroid
#print(data_buildings.head())

# get grid from postgis
sql_grid = "SELECT * FROM data.fi_grid_250m WHERE xyind = '3663756679375' OR xyind = '3733756685375' OR xyind = '3666256673875' OR xyind = '3763756680375' OR xyind = '3668756673375'"
grid_geom_column = 'wkb_geometry'
data_grid = gpd.read_postgis(sql_grid, con, geom_col=grid_geom_column)
#print(data_grid.head())

# display contents in a plot to visual check it if needed

'''
# buildings to plot
plt.rcParams['figure.figsize'] = [12, 6]
data_buildings.plot()
plt.title("Buildings data")
plt.show()
'''

'''
# grid to plot
plt.rcParams['figure.figsize'] = [12, 6]
data_grid.plot()
plt.title("Grid data")
plt.show()
'''

# spatial join xyind from grid to building centroids
buildings_grid = data_buildings.sjoin(data_grid, how="left", predicate="within")
buildings_grid = buildings_grid[["KERROSALA", "POLTTOAINE", "KAYTTOTARKOITUS", "VALMISTUNUT","geometry","xyind"]]
print(buildings_grid)


kerrosala_mean = buildings_grid.groupby(by=["xyind"], dropna=False).mean()

# check sjoin result visually
'''
plt.rcParams['figure.figsize'] = [12, 6]
join_left_df.plot()
plt.title("sjoin result")
plt.show()
'''
#DataFrame.aggregate(func=None, axis=0, *args, **kwargs)
result = buildings_grid.groupby('xyind')['KERROSALA'].aggregate('sum')
print(result)
#result = df.groupby('Courses')['Fee','Discount'].aggregate('sum')
# create result geodataframe?


# aggregate wanted building stats by xyind to result table
# figure out what column structure is needed (time periods, building types...)
# create a new dataframe?


# push result back to postgis