import os
from fastapi import Depends, FastAPI
from sqlmodel import SQLModel, create_engine, select

app = FastAPI()
DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)

from models import built, delineations, energy, grid_globals, traffic

SQLModel.metadata.create_all(engine)

@app.get("/")
def read_root():
    return {"Hello": "World"}