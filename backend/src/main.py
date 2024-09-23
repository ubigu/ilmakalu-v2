from fastapi import Depends, FastAPI
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session, init_db
from models import built, delineations, energy, grid_globals, traffic

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}