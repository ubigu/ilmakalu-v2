from __future__ import annotations
import pandas as pd
import geopandas as gpd
#import numpy as np

class EspooVaranto:
    """
    Class to hold Espoo varanto data.
    """
    def __init__(self):
        self._df = None

    def init_from_mock_gpkg(self, filename : str, layer : str) -> None:
        """
        Init from mock Espoo JSON data dump.
        """
        schema = {
            "geometry": "Polygon",
            "properties": {
                "alue", str,
                "code", str,
                "type", str,
                "status", str,
                "kem2", int,
                "year_completion", int,
                "owner", int
            }
        }
        df = gpd.read_file(filename, layer=layer, schema=schema)
        kem_sum = df.groupby(['code'])['kem2'].sum()
        df_total = df.join(kem_sum, on='code', rsuffix="_total")
        df_total['kem2_fraction'] = df_total.kem2 / df_total.kem2_total
        self._df = df_total


    def with_json(self, filename : str) -> EspooVaranto:
        self._df = gpd.read_file(filename)
        return self

    def df(self) -> gpd.GeoDataFrame:
        return self._df

class VasaraVaranto:
    """
    Class to hold Vasara varanto data.
    """
    def __init__(self):
        self._df = None

    def init_from_dump_json(self, filename) -> None:
        """
        Init from Vasara dump JSON.
        """
        # TODO:
        # schema would be fine way to handle data type conversion,
        # but nullable integer data types do not seem to work with
        # this method
        schema = {
            "geometry": "Polygon",
            "properties": {
                "alue", str,
                "code", str,
                "type", str,
                "status", str,
                "kem2", int,
                "year_completion", int,
                "owner", int
            }
        }
        df = gpd.read_file(filename, schema=schema)

        # nullable integer data types do not work with "schema" approach
        df['year_completion'] = df['year_completion'].astype('Int32')
        df['owner'] = df['owner'].astype("Int32")
        kem_sum = df.groupby(['code'])['kem2'].sum()
        df_total = df.join(kem_sum, on='code', rsuffix="_total")
        df_total['kem2_fraction'] = df_total.kem2 / df_total.kem2_total
        self._df = df_total

    def df(self) -> gpd.GeoDataFrame:
        return self._df