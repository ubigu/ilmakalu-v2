import json
from abc import ABC, abstractmethod
from datetime import datetime

import geopandas as gpd
import pandas as pd
from fastapi import HTTPException, Response
from pygeojson import FeatureCollection
from sqlalchemy import URL
from sqlalchemy.pool import NullPool
from sqlmodel import Session, create_engine, text

from db import engine
from grid import generate_grid
from models import user_input, user_output

geom_col = "geom"
crs = "EPSG:3067"


class CO2Query(ABC):
    def __init__(self, params, headers=None, body={}):
        if params.baseYear is not None and params.targetYear is not None and params.targetYear <= params.baseYear:
            raise HTTPException(status_code=400, detail="The base year should be smaller than the target year")

        try:
            self.params = params
            self.headers = headers
            self.layers = None if "layers" not in body else body["layers"]
            self.db = (
                engine
                if "connParams" not in body
                else create_engine(
                    URL.create(**({"drivername": "postgresql"} | json.loads(body["connParams"]))), poolclass=NullPool
                )
            )

            self.input_tables = {}
        except Exception as e:
            print(e)
            raise HTTPException(status_code=500, detail=repr(e))

    def __geoJSON_to_table(self, features, name):
        if isinstance(features, FeatureCollection):
            features = features.features

        gpd.GeoDataFrame.from_features(features, crs=crs).rename_geometry(geom_col).to_postgis(
            name, self.db, schema=user_input.schema
        )

    def __generate_grid(self, session):
        centroids = None
        for mun in self.params.mun:
            stmt = text("SELECT COUNT(xyind) FROM delineations.grid WHERE mun = :mun").bindparams(mun=mun)
            # Do not generate a grid if it already exists
            if session.exec(stmt).one()[0] > 0:
                continue
            if centroids is None:
                centroids = gpd.GeoDataFrame.from_postgis(
                    "SELECT geom, id FROM delineations.centroids", self.db, crs=3067
                )
            generate_grid(mun, centroids).to_postgis("grid", self.db, schema="delineations", if_exists="append")

    def __upload_layers(self):
        if self.layers is None:
            return

        layers = json.loads(self.layers)
        for layer in layers:
            base_name = layer["base"]
            layer_name = layer["name"]
            self.input_tables[base_name] = layer_name

            self.__geoJSON_to_table(layer["features"], layer_name)

    def __execute(self, session):
        result = session.exec(self.get_stmt()).mappings().all()
        return self.__format_output(result)

    def __clean_up(self, session):
        for table in self.input_tables.values():
            session.exec(text(f'DROP TABLE {user_input.schema}."{table}"'))

    def __format_output(self, result):
        if not isinstance(self.params.outputFormat, str):
            return result

        data = pd.DataFrame.from_records(result)
        match self.params.outputFormat.lower():
            case "xml":
                return Response(content=data.to_xml(index=False), media_type="application/xml")
            case "geojson":
                if geom_col not in data.columns:
                    gdf = gpd.GeoDataFrame(columns=[geom_col], geometry=geom_col, crs=crs)
                else:
                    data[geom_col] = gpd.GeoSeries.from_wkt(data[geom_col])
                    gdf = gpd.GeoDataFrame(data, geometry=geom_col, crs=crs)
                return Response(content=gdf.to_json(drop_id=True), media_type="application/geojson")
            case _:
                return result

    def __write_session_info(self, session):
        if self.headers is None or self.headers.uuid is None or self.headers.user is None:
            return

        p = self.params
        session.add(
            user_output.sessions(
                uuid=self.headers.uuid,
                user=self.headers.user,
                startTime=datetime.now().strftime("%Y%m%d_%H%M%S"),
                baseYear=p.calculationYear if p.baseYear is None else p.baseYear,
                targetYear=p.targetYear,
                calculationScenario=p.calculationScenario,
                method=p.method,
                electricityType=p.electricityType,
                geomArea=p.mun,
            )
        )

    def get_table_name(self, base, default):
        return default if base not in self.input_tables else user_input.schema + "." + self.input_tables[base]

    def execute(self):
        result = {}
        try:
            with Session(self.db) as session:
                session.begin()
                try:
                    self.__generate_grid(session)
                    self.__upload_layers()
                    result = self.__execute(session)
                except Exception:
                    session.rollback()
                    raise
                else:
                    self.__write_session_info(session)
                finally:
                    self.__clean_up(session)
                    session.commit()
            return result
        except Exception as e:
            print(e)
            raise HTTPException(status_code=500, detail=repr(e))

    @abstractmethod
    def get_stmt(self):
        pass
