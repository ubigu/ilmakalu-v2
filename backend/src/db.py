import os

from fastapi import HTTPException
from sqlmodel import SQLModel, create_engine

from models import built, delineations, energy, grid_globals, traffic, user_input

built
delineations
energy
grid_globals
traffic

engine = create_engine(os.environ.get("DATABASE_URL"))


def init_db():
    SQLModel.metadata.create_all(engine)
    SQLModel.metadata.reflect(engine, schema=user_input.schema)


def get_table_name(body, base, default):
    if body is None:
        return default
    next_layer = next((layer for layer in body["layers"] if layer["base"] == base), None)
    return default if next_layer is None else user_input.schema + "." + next_layer["name"]


def validate_years(base, target):
    if base is not None and target is not None and target <= base:
        raise HTTPException(status_code=400, detail="The base year should be smaller than the target year")
