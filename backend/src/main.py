from fastapi import FastAPI
from models import built, delineations, energy, grid_globals, traffic
from database import engine, Base

app = FastAPI()
Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {"Hello": "World"}