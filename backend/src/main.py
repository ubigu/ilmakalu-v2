from fastapi import FastAPI

from db import init_db
from routers import co2_calculate_emissions, co2_calculate_emissions_loop, co2_grid_processing

init_db()

app = FastAPI(swagger_ui_parameters={"syntaxHighlight": False})

app.include_router(co2_calculate_emissions.router)
app.include_router(co2_calculate_emissions_loop.router)
app.include_router(co2_grid_processing.router)
