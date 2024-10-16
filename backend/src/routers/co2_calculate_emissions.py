from fastapi import APIRouter, Query, Body
from sqlmodel import text, SQLModel
from typing import Annotated, Literal

from models.user_input import schema
from db import execute, validate_years, insert_data
from typings import UserInput

router = APIRouter(
    prefix="/co2-calculate-emissions",
    tags=["CO2 Calculate Emissions"]
)

class __CommonParams(SQLModel):
    calculationYear: int
    mun: Annotated[list[int], Query()] = []
    aoi: str | None = None
    calculationScenario: str = 'wem'
    method: Literal['em','hjm'] = 'em'
    electricityType: Literal['hankinta','tuotanto'] = 'tuotanto'
    baseYear: int | None = None
    targetYear: int | None = None
    plan_areas: str | None = None
    plan_transit: str | None = None
    plan_centers: str | None = None
    includeLongDistance: bool = True
    includeBusinessTravel: bool = True
    outputFormat: str | None = None

def __run_query(
    p: Annotated[__CommonParams, Query()],
    body: dict | None = None
):
    validate_years(p.baseYear, p.targetYear)
    stmt = text(
        """SELECT
            ST_AsText(geom) as geom, xyind, mun, zone,
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
            calculationYear => :calculationYear,
            calculationScenario => :calculationScenario,
            method => :method,
            electricityType => :electricityType,
            baseYear => :baseYear,
            targetYear => :targetYear,
            plan_areas => :plan_areas,
            plan_transit => :plan_transit,
            plan_centers => :plan_centers,
            includeLongDistance => :includeLongDistance,
            includeBusinessTravel => :includeBusinessTravel
        );"""
    )
    stmt = stmt.bindparams(
        municipalities=p.mun,
        aoi=f'{schema}.aoi' if body is not None and 'aoi' in body.keys() else p.aoi,
        calculationYear=p.calculationYear,
        calculationScenario=p.calculationScenario,
        method=p.method,
        electricityType=p.electricityType,
        baseYear=p.baseYear,
        targetYear=p.targetYear,
        plan_areas=f'{schema}.plan_areas' if body is not None and 'plan_areas' in body.keys() else p.plan_areas,
        plan_transit=f'{schema}.plan_transit' if body is not None and 'plan_transit' in body.keys() else p.plan_transit,
        plan_centers=f'{schema}.plan_centers' if body is not None and 'plan_centers' in body.keys() else p.plan_centers,
        includeLongDistance=p.includeLongDistance,
        includeBusinessTravel=p.includeBusinessTravel,
    )
    return execute(stmt, p.outputFormat)

@router.get(
    "/",
    responses={404: {"description": "Bad request"}},
)
def CO2_CalculateEmissions_get(
    params: Annotated[__CommonParams, Query()]
):
    return __run_query(params)

@router.post(
    "/",
    responses={404: {"description": "Bad request"}},
)
def CO2_CalculateEmissions_post(
    params: Annotated[__CommonParams, Query()],
    body: Annotated[UserInput, Body()],
):
    insert_data(body)
    return __run_query(params, body)