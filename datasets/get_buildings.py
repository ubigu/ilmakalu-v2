import geopandas as gpd
from requests import Request
from owslib.wfs import WebFeatureService
from sqlalchemy import create_engine
from modules.config import Config
import matplotlib.pyplot as plt
from shapely.geometry.polygon import Polygon
from shapely.geometry.multipolygon import MultiPolygon

# Articles for background
# https://gis.stackexchange.com/questions/299567/reading-data-to-geopandas-using-wfs
# https://gis.stackexchange.com/questions/239198/adding-geopandas-dataframe-to-postgis-table

# Create config object for database
cfg = Config()

# Setup WFS service
url = cfg.wfs_url()
wfs = WebFeatureService(url=url)

# Specify the parameters for fetching the data. Note that GML is assumed as an output format.
params = cfg.wfs_params()

# Parse the URL with parameters
q = Request('GET', url, params=params).prepare().url

# Read data from URL into a geodataframe
data = gpd.read_file(q, driver='GML')

# Take a copy of the geodataframe with only wanted columns
data_limited = data[[cfg.floor_area_attribute(), cfg.fuel_attribute(), cfg.building_type_attribute(), "geometry"]]

# Go through the geodataframe and check how what geometry types are present and how many of them exist
geom_counts = {'Polygon':0, 'MultiPolygon':0, 'LineString':0, 'MultiLineString':0, 'Point': 0, 'MultiPoint':0, 'Empty': 0, 'Missing':0}

for index, row in data_limited.iterrows( ):
    if row.geometry.geom_type == 'Polygon':
        geom_counts['Polygon'] += 1
    elif row.geometry.geom_type == 'MultiPolygon':
        geom_counts['MultiPolygon'] += 1
    elif row.geometry.geom_type == 'LineString':
        geom_counts['LineString'] += 1
    elif row.geometry.geom_type == 'MultiLineString':
        geom_counts['MultiLineString'] += 1
    elif row.geometry.geom_type == 'Point':
        geom_counts['Point'] += 1
    elif row.geometry.geom_type == 'MultiPoint':
        geom_counts['MultiPoint'] += 1
    elif row.geometry.isna():
        geom_counts['Missing'] += 1
    elif row.geometry.isempty:
        geom_counts['Empty'] += 1
    else:
        raise ValueError("Geodataframe contains a row which geometry type can't be handled.")

print(f"Data contains the following geometry types: {geom_counts}")

# In case data contained other geometry types than polygon and multipolygon, do some clean up
if geom_counts['Point'] > 0:
    data_limited = data_limited[data_limited.geom_type != 'Point']
if geom_counts['MultiPoint'] > 0:
    data_limited = data_limited[data_limited.geom_type != 'MultiPoint']
if geom_counts['LineString'] > 0:
    data_limited = data_limited[data_limited.geom_type != 'LineString']
if geom_counts['MultiLineString'] > 0:
    data_limited = data_limited[data_limited.geom_type != 'MultiLineString']

# In case data contains polygons, force them to multitype
if geom_counts['Polygon'] > 0:
    data_limited["geometry"] = [MultiPolygon([feature]) if isinstance(feature, Polygon) else feature for feature in data_limited["geometry"]]

# todo: quality control for empty and missing geometries

# Create database engine and push geodataframe to Postgres as a PostGIS table
engine = create_engine(cfg._db_connection_url("local_dev"))

data_limited.to_postgis(
    con=engine,
    name="rakennukset",
    schema="data",
    if_exists='replace',
)

'''
# Display geodataframe contents to a plot
plt.rcParams['figure.figsize'] = [12, 6]
data.plot()
plt.title("Buildings data")
plt.show()
'''