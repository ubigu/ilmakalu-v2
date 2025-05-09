import geopandas as gpd
import pandas as pd
from requests import Request
from owslib.wfs import WebFeatureService
from sqlalchemy import create_engine
from modules.config import Config
import matplotlib.pyplot as plt
from shapely.geometry.polygon import Polygon
from shapely.geometry.multipolygon import MultiPolygon
from collections import Counter
from datetime import datetime

'''
This script gets buildings from WFS interface, does some quality checks
and corrections to them and finally pushes them to postgres. Add needed
parameters to config.yaml under wfs section before running. Note that 
this script fetches buildings from a service "as they are" and further
preprocessing might be reasonable depending on the data. 

Articles referenced here:
https://gis.stackexchange.com/questions/299567/reading-data-to-geopandas-using-wfs
https://gis.stackexchange.com/questions/239198/adding-geopandas-dataframe-to-postgis-table
'''

# create config object for database and a connection
cfg = Config()
pg_connection = create_engine(cfg._db_connection_url())

# Setup WFS service
url = cfg.wfs_url()
wfs = WebFeatureService(url=url)

# Specify the parameters for fetching the data. Note that GML is assumed as an output format.
params = cfg.wfs_params()

# parse the URL with parameters
q = Request('GET', url, params=params).prepare().url

# read data from URL into a geodataframe
original_data = gpd.read_file(q, driver='GML')

# take a copy of the geodataframe with only wanted columns
data = original_data[[cfg.floor_area_attribute(), cfg.fuel_attribute(), cfg.building_code_attribute(), cfg.year_attribute(), "geometry"]]

# rename columns
data = data.rename(columns={cfg.year_attribute():"year",cfg.building_code_attribute():"building_type",cfg.fuel_attribute():"fuel",cfg.floor_area_attribute():"floor_area"})

# in Espoo construction year is announced in DD.MM.YYYY format
# pandas native datetime datatype has nanosecond resolution so we use python's datetime in conversion. Null values are left as is.
data["year"] = data["year"].apply(lambda x : datetime.strptime(x, "%d.%m.%Y").year if pd.notnull(x) else x).astype('Int64')

# Due to possible null values pandas might have converted building type column to float64. Convert it back to Int64.
data['building_type'] = data['building_type'].astype("Int64")

# Go through the geodataframe and check how what geometry types are present and how many of them exist
geom_counts = Counter()
for index, row in data.iterrows():
    geom_counts[row.geometry.geom_type] += 1
print(f"Data contains the following geometry types: {geom_counts}")

# Check if data is missing geometry field for some rows and warn user if this is the case
missing_geom_field_count = data["geometry"].isna().sum()
if missing_geom_field_count > 0:
    print(f"WARNING: Data included {str(missing_geom_field_count)} rows without geometry column.")

# Go through the geodataframe and check if any rows miss geometry values (but have the column)
missing_geom_value_count = data["geometry"].is_empty.sum()
if missing_geom_value_count > 0:
    print(f"WARNING: Data included {str(missing_geom_value_count)} rows without geometry value.")

# In case data contains polygons, force them to multitype
if geom_counts['Polygon'] > 0:
    data["geometry"] = [MultiPolygon([feature]) if isinstance(feature, Polygon) else feature for feature in data["geometry"]]

# Make sure that data doesn't contain any points or lines
data = data[data.geom_type == 'MultiPolygon']

# Create database engine and push geodataframe to Postgres as a PostGIS table
data.to_postgis(
    con=pg_connection,
    name="buildings",
    schema="data",
    if_exists='replace',
)

# add identity field to the table
with pg_connection.connect() as con_pk:
    con_pk.execute('ALTER TABLE data.buildings ADD COLUMN id int GENERATED BY DEFAULT AS IDENTITY')

'''
# Display geodataframe contents to a plot
plt.rcParams['figure.figsize'] = [12, 6]
data.plot()
plt.title("Buildings data")
plt.show()
'''
