import os

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
