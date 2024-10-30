import os
import warnings

import geopandas as gp
import pandas as pd
from fastapi import HTTPException, Response
from pydantic import create_model
from pygeojson import FeatureCollection
from shapely import geometry, wkb, wkt
from sqlmodel import Session, SQLModel, create_engine

from models import built, delineations, energy, grid_globals, traffic, user_input

built
delineations
energy
grid_globals
traffic

engine = create_engine(os.environ.get("DATABASE_URL"))
tables = SQLModel.metadata.tables

geom_col = "geom"
crs = "EPSG:3067"


def init_db():
    SQLModel.metadata.create_all(engine)
    SQLModel.metadata.reflect(engine, schema=user_input.schema)


def __get_base(base_name):
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


def get_table_name(body, base, default):
    if body is None:
        return default
    next_layer = next((layer for layer in body["layers"] if layer["base"] == base), None)
    return default if next_layer is None else user_input.schema + "." + next_layer["name"]


def __drop_table(table):
    table.drop(engine)
    SQLModel.metadata.remove(table)


def __geoJSON_to_mappings(features):
    if isinstance(features, FeatureCollection):
        features = features.features

    return [
        {
            geom_col: wkb.dumps(wkt.loads(geometry.shape(f.geometry.__dict__).wkt), hex=True, srid=3067),
            **f.properties,
        }
        for f in features
    ]


def insert_data(body):
    with Session(engine) as session:
        for layer in body["layers"]:
            base = __get_base(layer["base"])

            full_name = f"{user_input.schema}.{layer["name"]}"
            if full_name in tables:
                warnings.warn(f"An already existing table {full_name} will be replaced", ImportWarning)
                __drop_table(tables[full_name])

            try:
                Model = create_model(layer["name"], __base__=base, __cls_kwargs__={"table": True})
                SQLModel.metadata.create_all(engine)
                session.bulk_insert_mappings(Model, __geoJSON_to_mappings(layer["features"]))
            except Exception as error:
                raise HTTPException(status_code=400, detail=f"Failed to import the data: {error}")
        session.commit()


def validate_years(base, target):
    if base is not None and target is not None and target <= base:
        raise HTTPException(status_code=400, detail="The base year should be smaller than the target year")


def execute(stmt, outputFormat):
    if isinstance(outputFormat, str):
        outputFormat = outputFormat.lower()

    all_mappings = {}
    with Session(engine) as session:
        all_mappings = session.exec(stmt).mappings().all()

    data = pd.DataFrame.from_records(all_mappings)
    match outputFormat:
        case "xml":
            return Response(content=data.to_xml(index=False), media_type="application/xml")
        case "geojson":
            if geom_col not in data.columns:
                gdf = gp.GeoDataFrame(columns=[geom_col], geometry=geom_col, crs=crs)
            else:
                data[geom_col] = gp.GeoSeries.from_wkt(data[geom_col])
                gdf = gp.GeoDataFrame(data, geometry=geom_col, crs=crs)
            return Response(content=gdf.to_json(drop_id=True), media_type="application/geo+json")
        case _:
            return all_mappings
