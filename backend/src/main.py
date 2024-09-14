from fastapi import FastAPI

from . import models

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}