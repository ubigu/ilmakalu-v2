import os

from sqlmodel import SQLModel, create_engine

from models import built, delineations, energy, grid_globals, traffic, user_input

built
delineations
energy
grid_globals
traffic

url = os.environ.get("DATABASE_URL")
if url is not None:
    engine = create_engine(url)


def init_db():
    SQLModel.metadata.create_all(engine)
    SQLModel.metadata.reflect(engine, schema=user_input.schema)
