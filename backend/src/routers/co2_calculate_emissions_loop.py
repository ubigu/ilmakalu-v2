from fastapi import APIRouter, Query, Body
from sqlmodel import text
from typing import Annotated, Literal

from db import execute, validate_years, insert_data, geom_col
from typings import UserInput

router = APIRouter(
    prefix=f"/co2-calculate-emissions-loop",
    tags=["CO2 Calculate Emissions Loop"],
)

__stmt = text(
    f"""SELECT
        ST_AsText({geom_col}) as {geom_col}, xyind, mun, zone,
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

@router.get(
        "/",
        responses={404: {"description": "Bad request"}},
)
def CO2_CalculateEmissionsLoop_get(
    baseYear: int,
    targetYear: int,
    mun: Annotated[list[int], Query()] = [],
    aoi: str | None = None,
    calculationScenario: str = 'wem',
    method: Literal['em','hjm'] = 'em',
    electricityType: Literal['hankinta','tuotanto'] = 'tuotanto',
    plan_areas: str | None = None,
    plan_transit: str | None = None,
    plan_centers: str | None = None,
    includeLongDistance: bool = True,
    includeBusinessTravel: bool = True,
    outputFormat: str | None = None
):
    validate_years(baseYear, targetYear)

    return execute(__stmt.bindparams(
        municipalities=mun,
        aoi=aoi,
        calculationScenario=calculationScenario,
        method=method,
        electricityType=electricityType,
        baseYear=baseYear,
        targetYear=targetYear,
        plan_areas=plan_areas,
        plan_transit=plan_transit,
        plan_centers=plan_centers,
        includeLongDistance=includeLongDistance,
        includeBusinessTravel=includeBusinessTravel
    ), outputFormat)

@router.post(
        "/",
        responses={404: {"description": "Bad request"}},
)
def CO2_CalculateEmissionsLoop_post(
    body: Annotated[UserInput, Body()],
    baseYear: int,
    targetYear: int,
    mun: Annotated[list[int], Query()] = [],
    aoi: str | None = None,
    calculationScenario: str = 'wem',
    method: Literal['em','hjm'] = 'em',
    electricityType: Literal['hankinta','tuotanto'] = 'tuotanto',
    plan_areas: str | None = None,
    plan_transit: str | None = None,
    plan_centers: str | None = None,
    includeLongDistance: bool = True,
    includeBusinessTravel: bool = True,
    outputFormat: str | None = None
):
    insert_data(body)
    validate_years(baseYear, targetYear)
    body_keys = body.keys()
    return execute(__stmt.bindparams(
        municipalities=mun,
        aoi='user_input.aoi' if 'aoi' in body_keys else aoi,
        calculationScenario=calculationScenario,
        method=method,
        electricityType=electricityType,
        baseYear=baseYear,
        targetYear=targetYear,
       plan_areas='user_input.plan_areas' if 'plan_areas' in body_keys else plan_areas,
        plan_transit='user_input.plan_transit' if 'plan_transit' in body_keys else plan_transit,
        plan_centers='user_input.plan_centers' if 'plan_centers' in body_keys else plan_centers,
        includeLongDistance=includeLongDistance,
        includeBusinessTravel=includeBusinessTravel
    ), outputFormat)