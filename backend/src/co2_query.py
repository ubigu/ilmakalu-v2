import geopandas as gp
import pandas as pd
from fastapi import HTTPException, Response
from pydantic import create_model
from pygeojson import FeatureCollection
from shapely import geometry, wkb, wkt
from sqlalchemy.ext.declarative import declarative_base
from sqlmodel import Session, SQLModel, text

from db import engine
from models import user_input

geom_col = "geom"

tables = SQLModel.metadata.tables


Base = declarative_base()
SQLModel.metadata.drop_all


class CO2Query:
    def __init__(self, stmt, layers=None):
        self.stmt = stmt
        self.layers = layers

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
        if not self.layers:
            return

        for layer in self.layers:
            base = self.__get_base(layer["base"])
            layer_name = layer["name"]
            self.__drop_table_if_exists(session, layer_name)

            Model = create_model(layer_name, __base__=base, __cls_kwargs__={"table": True})
            tables[f"{user_input.schema}.{layer_name}"].create(engine, checkfirst=True)
            session.bulk_insert_mappings(Model, self.__geoJSON_to_mappings(layer["features"]))

    def __clean_up(self, session):
        if self.layers:
            for layer in self.layers:
                self.__drop_table_if_exists(session, layer["name"])

    def __format_output(self, result, outputFormat):
        crs = "EPSG:3067"
        data = pd.DataFrame.from_records(result)
        match outputFormat:
            case "xml":
                return Response(content=data.to_xml(index=False), media_type="application/xml")
            case "geojson":
                if geom_col not in data.columns:
                    gdf = gp.GeoDataFrame(columns=[geom_col], geometry=geom_col, crs=crs)
                else:
                    data[geom_col] = gp.GeoSeries.from_wkt(data[geom_col])
                    gdf = gp.GeoDataFrame(data, geometry=geom_col, crs=crs)
                return Response(content=gdf.to_json(drop_id=True), media_type="application/geojson")
            case _:
                return result

    def execute(self, outputFormat):
        if isinstance(outputFormat, str):
            outputFormat = outputFormat.lower()
        result = {}
        with Session(engine) as session:
            self.__upload_layers(session)
            result = session.exec(self.stmt).mappings().all()
            self.__clean_up(session)
            session.commit()
        return self.__format_output(result, outputFormat)
