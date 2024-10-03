from fastapi import APIRouter, HTTPException, Body
from pydantic import create_model
from typing import Annotated, Literal
from sqlmodel import SQLModel, Session, text
import warnings
import shapely

from main import engine, geometry_col
from models import user_input
router = APIRouter()

schema = user_input.schema
SQLModel.metadata.reflect(engine,schema=schema)
tables = SQLModel.metadata.tables

def __get_base(base_name):
    match base_name:
        case 'plan_areas':
            return user_input.plan_areas_base
        case 'plan_transit':
            return user_input.plan_transit_base
        case 'plan_centers':
            return user_input.plan_centers_base
        case 'aoi':
            return user_input.aoi_base
        case _:
            HTTPException(
                status_code=400,
                detail=f"The base {base_name} was not found"
            )

def __drop_table(table):
    table.drop(engine)
    SQLModel.metadata.remove(table)

def __geoJSON_to_mappings(features):
    if isinstance(features, dict) and features['features']:
        features = features['features']
    return [{
        geometry_col: shapely.set_srid(shapely.geometry.shape(f['geometry']),3067).wkt,
        **f['properties']
    } for f in features]
    
@router.post("/data/{base_name}")
def insert_data(
    base_name: Literal['plan_areas','plan_transit','plan_centers','aoi'],
    body: Annotated[object, Body()],
    name: str | None = None
):
    base = __get_base(base_name)

    if name is None:
        name = base_name
    full_name = f'{schema}.{name}'
    if full_name in tables:
        warnings.warn(f"An already existing table {full_name} will be replaced", ImportWarning)
        __drop_table(tables[full_name])

    Model = create_model(
        name,
        __base__=base,
        __cls_kwargs__={"table": True}
    )
    SQLModel.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            session.bulk_insert_mappings(Model, __geoJSON_to_mappings(body))
            session.commit()

            return session.exec(text(f"SELECT * FROM {full_name}")).mappings().all()
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to import data: {error}"
        )