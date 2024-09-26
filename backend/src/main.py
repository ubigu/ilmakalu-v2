import os
from fastapi import FastAPI, Query, Response
from sqlmodel import SQLModel, Session, create_engine, text
from typing import Annotated
from datetime import datetime
import pandas as pd
import geopandas as gp

app = FastAPI()
DATABASE_URL = os.environ.get('DATABASE_URL')
engine = create_engine(DATABASE_URL)

from models import built, delineations, energy, grid_globals, traffic
SQLModel.metadata.create_all(engine)

geometry_col = 'geom'
crs = 'EPSG:3067'

def __execute(stmt, outputformat):
    if type(outputformat) == str:
        outputformat = outputformat.lower()

    with Session(engine) as session:
        all =  session.exec(stmt).mappings().all()
        data = pd.DataFrame.from_records(all)
        match outputformat:
            case 'xml':
                return Response(
                    content=data.to_xml(index=False),
                    media_type="application/xml"
                )
            case 'geojson':
                if geometry_col not in data.columns:
                    gdf = gp.GeoDataFrame(columns=[geometry_col], geometry=geometry_col, crs=crs)
                else:
                    data[geometry_col] = gp.GeoSeries.from_wkt(data[geometry_col])
                    gdf = gp.GeoDataFrame(data, geometry=geometry_col, crs=crs)
                return Response(
                    content=gdf.to_json(drop_id=True),
                    media_type="application/geo+json"
                )
            case _:
                return all
    
@app.get("/co2-calculate-emissions/")
def CO2_CalculateEmissions(
    mun: Annotated[list[int], Query()] = [],
    aoi: str | None = None,
    includeLongDistance: bool = False,
    includeBusinessTravel: bool = True,
    year: Annotated[list[int], Query()] = [datetime.now().year,2017,2050],
    calculationScenario: str = 'wem',
    method: str = 'em',
    electricityType: str = 'tuotanto',
    baseYear: int | None = None,
    targetYear: int | None = None,
    plan_areas: str | None = None,
    plan_centers: str | None = None,
    plan_transit: str | None = None,
    outputformat: str | None = None
):
    stmt = text(
        f"""SELECT
            ST_AsText(geom) as {geometry_col}, xyind, mun, zone,
            date_part('year', year) as year, floorspace, pop,
            employ, tilat_vesi_tco2, tilat_lammitys_tco2,
            tilat_jaahdytys_tco2, sahko_kiinteistot_tco2,
            sahko_kotitaloudet_tco2, sahko_palv_tco2,
            sahko_tv_tco2, liikenne_as_tco2, liikenne_tp_tco2,
            liikenne_tv_tco2, liikenne_palv_tco2,
            rak_korjaussaneeraus_tco2, rak_purku_tco2,
            rak_uudis_tco2, sum_yhteensa_tco2, sum_lammonsaato_tco2,
            sum_liikenne_tco2, sum_sahko_tco2, sum_rakentaminen_tco2
        FROM functions.CO2_CalculateEmissions(
            municipalities => :municipalities,
            aoi => :aoi,
            includeLongDistance => :includeLongDistance,
            includeBusinessTravel => :includeBusinessTravel,
            calculationYears => :calculationYears,
            calculationScenario => :calculationScenario,
            method => :method,
            electricityType => :electricityType,
            baseYear => :baseYear,
            targetYear => :targetYear,
            plan_areas => :plan_areas,
            plan_centers => :plan_centers,
            plan_transit => :plan_transit 
        );"""
    )
    stmt = stmt.bindparams(
        municipalities=mun,
        aoi=aoi,
        includeLongDistance=includeLongDistance,
        includeBusinessTravel=includeBusinessTravel,
        calculationYears=year,
        calculationScenario=calculationScenario,
        method=method,
        electricityType=electricityType,
        baseYear=baseYear,
        targetYear=targetYear,
        plan_areas=plan_areas,
        plan_centers=plan_centers,
        plan_transit=plan_transit
    )
    return __execute(stmt, outputformat)
    
@app.get("/co2-calculate-emissions-loop/")
def CO2_CalculateEmissionsLoop(
    mun: Annotated[list[int], Query()] = [],
    aoi: str | None = None,
    includeLongDistance: bool = False,
    includeBusinessTravel: bool = True,
    calculationScenario: str = 'wem',
    method: str = 'em',
    electricityType: str = 'tuotanto',
    baseYear: int | None = None,
    targetYear: int | None = None,
    plan_areas: str | None = None,
    plan_centers: str | None = None,
    plan_transit: str | None = None,
    outputformat: str | None = None
):
    stmt = text(
        f"""SELECT
            ST_AsText(geom) as {geometry_col}, xyind, mun, zone,
            date_part('year', year) as year, floorspace, pop,
            employ, tilat_vesi_tco2, tilat_lammitys_tco2,
            tilat_jaahdytys_tco2, sahko_kiinteistot_tco2,
            sahko_kotitaloudet_tco2, sahko_palv_tco2,
            sahko_tv_tco2, liikenne_as_tco2, liikenne_tp_tco2,
            liikenne_tv_tco2, liikenne_palv_tco2,
            rak_korjaussaneeraus_tco2, rak_purku_tco2,
            rak_uudis_tco2, sum_yhteensa_tco2, sum_lammonsaato_tco2,
            sum_liikenne_tco2, sum_sahko_tco2, sum_rakentaminen_tco2
        FROM functions.CO2_CalculateEmissionsLoop(
            municipalities => :municipalities,
            aoi => :aoi,
            includeLongDistance => :includeLongDistance,
            includeBusinessTravel => :includeBusinessTravel,
            calculationScenario => :calculationScenario,
            method => :method,
            electricityType => :electricityType,
            baseYear => :baseYear,
            targetYear => :targetYear,
            plan_areas => :plan_areas,
            plan_centers => :plan_centers,
            plan_transit => :plan_transit 
        );"""
    ).bindparams(
        municipalities=mun,
        aoi=aoi,
        includeLongDistance=includeLongDistance,
        includeBusinessTravel=includeBusinessTravel,
        calculationScenario=calculationScenario,
        method=method,
        electricityType=electricityType,
        baseYear=baseYear,
        targetYear=targetYear,
        plan_areas=plan_areas,
        plan_centers=plan_centers,
        plan_transit=plan_transit
    )
    return __execute(stmt, outputformat)
    