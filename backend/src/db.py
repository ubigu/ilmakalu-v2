import os

from sqlmodel import SQLModel, create_engine

from models import built, delineations, energy, grid_globals, traffic, user_input

built
delineations
energy
grid_globals
traffic

url = os.environ.get("DATABASE_URL")
engine = create_engine(url) if url is not None else None


def init_db():
    """Initialize the database by creating tables stored in the
    metadata and loading available table definitions from the schema user_input"""
    if engine is None:
        return
    SQLModel.metadata.create_all(engine)
    SQLModel.metadata.reflect(engine, schema=user_input.schema)
