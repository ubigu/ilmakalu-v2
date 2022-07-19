import geopandas as gpd
from requests import Request
from owslib.wfs import WebFeatureService
from sqlalchemy import create_engine
from modules.config import Config

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

# For some reason WFS output in geodataframe has no CRS information
print(data.geometry.crs)

# Create database engine and push geodataframe to Postgres as a PostGIS table
engine = create_engine(cfg._db_connection_url("local_dev"))

data.to_postgis(
    con=engine,
    name="rakennukset",
    schema="data"
)
