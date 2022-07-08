"""Helper module for centers."""

from dis import dis
from sqlalchemy import create_engine
import pandas as pd
import geopandas
from shapely.geometry import shape
from shapely.geometry.polygon import Polygon

class UrbanCenters:
    """Class to handle urban centers"""

    def __init__(self, db_uri : str):
        try:
            self._conn = create_engine(db_uri)
        except:
            raise Exception("Couldn't connect to database")
        sql = "SELECT fi_center_ref, ST_Transform(geom, 4326) AS geom FROM data.fi_center_p"
        self._centers = geopandas.GeoDataFrame.from_postgis(sql, self._conn)

    def df(self) -> geopandas.GeoDataFrame:
        return self._centers

class GridCells:
    """Obtain grid cells from one municipality"""
    def __init__(self, db_uri : str = None, natcode : str = None):
        try:
            self._conn = create_engine(db_uri)
        except:
            raise Exception("Couldn't connect to database")
        sql = (
            "SELECT xyind, ST_Centroid(ST_Transform(g.wkb_geometry, 4326)) AS geom "
            "FROM data.fi_grid_250m AS g "
            "JOIN data.fi_municipality_2022_10k AS mun "
            "ON ST_Intersects(mun.geom, g.wkb_geometry) WHERE natcode='{}'".format(natcode))
        self._gridcells = geopandas.GeoDataFrame.from_postgis(sql, self._conn)
        pass

    def df(self):
        return self._gridcells
class RoutingResult:
    """Class to handle computed routing results."""
    def __init__(self, db_uri : str):
        try:
            self._conn = create_engine(db_uri)
        except:
            raise Exception("Couldn't connect to database")

    def persist(self, result : pd.DataFrame, schema : str, table_name : str):
        result.to_sql(table_name, self._conn, schema, if_exists="replace")

class IsochroneResult:
    def __init__(self, db_uri : str):
        try:
            self._conn = create_engine(db_uri)
        except:
            raise Exception("Couldn't connect to database")
        self._isochrones = geopandas.GeoDataFrame()
    
    def df(self):
        return self._isochrones

    def add_row(self, center_id, distance, geometry):
        df = pd.DataFrame(
            {
                'fi_center_id': [center_id],
                'distance': [distance]
            })
        poly : Polygon = shape(geometry.get("geometry"))
        gdf = geopandas.GeoDataFrame(df, geometry=[poly], crs="EPSG:4326")

        self._isochrones = pd.concat([self._isochrones, gdf])

    def persist(self, distance=None):
        """Save results to database"""
        if distance is not None:
            df = self._isochrones[self._isochrones["distance"] == distance].copy()
            pass
        else:
            df = self._isochrones
        df.to_postgis("fi_center_isochrones", self._conn, "data", if_exists="append")
