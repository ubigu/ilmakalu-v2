from abc import ABC, abstractmethod
from datetime import datetime

import geopandas as gp
import pandas as pd
from fastapi import HTTPException, Response
from pydantic import create_model
from pygeojson import FeatureCollection
from shapely import geometry, wkb, wkt
from sqlalchemy.ext.declarative import declarative_base
from sqlmodel import Session, SQLModel, text

from db import engine
from models import user_input, user_output

geom_col = "geom"

tables = SQLModel.metadata.tables


Base = declarative_base()
SQLModel.metadata.drop_all


class CO2Query(ABC):
    def __init__(self, params, body={}, uuid=None, user=None):
        if params.baseYear is not None and params.targetYear is not None and params.targetYear <= params.baseYear:
            raise HTTPException(status_code=400, detail="The base year should be smaller than the target year")

        self.p = params
        self.body = body
        self.uuid = uuid
        self.user = user

    def __get_base(self, base_name):
        match base_name:
            case "plan_areas":
                return user_input.plan_areas_base
            case "plan_transit":
                return user_input.plan_transit_base
            case "plan_centers":
                return user_input.plan_centers_base
            case "aoi":
                return user_input.aoi_base
            case _:
                raise HTTPException(status_code=400, detail=f"The base {base_name} was not found")

    def get_table_name(self, base, default):
        if "layers" not in self.body:
            return default

        next_layer = next((layer for layer in self.body["layers"] if layer["base"] == base), None)
        return default if next_layer is None else user_input.schema + "." + next_layer["name"]

    def __drop_table_if_exists(self, session, name):
        full_name = f"{user_input.schema}.{name}"
        if full_name not in tables:
            return
        session.exec(text(f'DROP TABLE {user_input.schema}."{name}"'))
        SQLModel.metadata.remove(tables[full_name])

    def __geoJSON_to_mappings(self, features):
        if isinstance(features, FeatureCollection):
            features = features.features

        return [
            {
                geom_col: wkb.dumps(wkt.loads(geometry.shape(f.geometry.__dict__).wkt), hex=True, srid=3067),
                **f.properties,
            }
            for f in features
        ]

    def __upload_layers(self, session):
        if "layers" not in self.body:
            return

        for layer in self.body["layers"]:
            base = self.__get_base(layer["base"])
            layer_name = layer["name"]
            self.__drop_table_if_exists(session, layer_name)

            Model = create_model(layer_name, __base__=base, __cls_kwargs__={"table": True})
            tables[f"{user_input.schema}.{layer_name}"].create(engine, checkfirst=True)
            session.bulk_insert_mappings(Model, self.__geoJSON_to_mappings(layer["features"]))

    def __clean_up(self, session):
        if "layers" not in self.body:
            return

        for layer in self.body["layers"]:
            self.__drop_table_if_exists(session, layer["name"])

    def __format_output(self, result):
        if not isinstance(self.p.outputFormat, str):
            return result

        data = pd.DataFrame.from_records(result)
        match self.p.outputFormat.lower():
            case "xml":
                return Response(content=data.to_xml(index=False), media_type="application/xml")
            case "geojson":
                crs = "EPSG:3067"
                if geom_col not in data.columns:
                    gdf = gp.GeoDataFrame(columns=[geom_col], geometry=geom_col, crs=crs)
                else:
                    data[geom_col] = gp.GeoSeries.from_wkt(data[geom_col])
                    gdf = gp.GeoDataFrame(data, geometry=geom_col, crs=crs)
                return Response(content=gdf.to_json(drop_id=True), media_type="application/geojson")
            case _:
                return result

    def __write_session_info(self, session):
        if self.uuid is None or self.user is None:
            return
        session.add(
            user_output.sessions(
                uuid=self.uuid,
                user=self.user,
                startTime=datetime.now().strftime("%Y%m%d_%H%M%S"),
                baseYear=self.p.calculationYear if self.p.baseYear is None else self.p.baseYear,
                targetYear=self.p.targetYear,
                calculationScenario=self.p.calculationScenario,
                method=self.p.method,
                electricityType=self.p.electricityType,
                geomArea=self.p.mun,
            )
        )

    def execute(self):
        result = {}
        with Session(engine) as session:
            try:
                self.__upload_layers(session)
                result = session.exec(self.get_stmt()).mappings().all()
            except Exception:
                raise HTTPException(status_code=500)
            else:
                self.__write_session_info(session)
            finally:
                self.__clean_up(session)
                session.commit()
        return self.__format_output(result)

    @abstractmethod
    def get_stmt(self):
        pass
