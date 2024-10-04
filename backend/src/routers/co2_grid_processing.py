from fastapi import APIRouter, Query, Body
from sqlmodel import text
from typing import Annotated, Literal

from db import execute, validate_years, insert_data, geom_col
from typings import UserInput

route = 'co2-grid-processing'
router = APIRouter(
    prefix=f"/co2-grid-processing",
    tags=["CO2 Grid Processing"],
)

__stmt = text(
    f"""SELECT
        ST_AsText({geom_col}) as {geom_col}, xyind,
        mun, zone, maa_ha, centdist, pop, employ,
        k_ap_ala, k_ar_ala, k_ak_ala, k_muu_ala,
        k_poistuma, alueteho
    FROM functions.CO2_GridProcessing(
        municipalities => :municipalities,
        aoi => :aoi,
        calculationYear => :calculationYear,
        baseYear => :baseYear,
        targetYear => :targetYear,
        plan_areas => :plan_areas,
        plan_transit => :plan_transit,
        plan_centers => :plan_centers,
        km2hm2 => :km2hm2
    );"""
)

@router.get(
        "/",
        responses={404: {"description": "Bad request"}},
)
def CO2_GridProcessing_get(
    calculationYear: int,
    baseYear: int,
    mun: Annotated[list[int], Query()] = [],
    aoi: str | None = None,
    targetYear: int | None = None,
    plan_areas: str | None = None,
    plan_transit: str | None = None,
    plan_centers: str | None = None,
    km2hm2: float = 1.25,
    outputFormat: str | None = None
):
    validate_years(baseYear, targetYear)

    return execute(__stmt.bindparams(
        municipalities=mun,
        aoi=aoi,
        calculationYear=calculationYear,
        baseYear=baseYear,
        targetYear=targetYear,
        plan_areas=plan_areas,
        plan_transit=plan_transit,
        plan_centers=plan_centers,
        km2hm2=km2hm2
    ), outputFormat)

@router.post(
        "/",
        responses={404: {"description": "Bad request"}},
)
def CO2_GridProcessing_post(
    body: Annotated[UserInput, Body()],
    calculationYear: int,
    baseYear: int,
    mun: Annotated[list[int], Query()] = [],
    aoi: str | None = None,
    targetYear: int | None = None,
    plan_areas: str | None = None,
    plan_transit: str | None = None,
    plan_centers: str | None = None,
    km2hm2: float = 1.25,
    outputFormat: str | None = None
):
    insert_data(body)
    validate_years(baseYear, targetYear)
    body_keys = body.keys()
    return execute(__stmt.bindparams(
        municipalities=mun,
        aoi='user_input.aoi' if 'aoi' in body_keys else aoi,
        calculationYear=calculationYear,
        baseYear=baseYear,
        targetYear=targetYear,
        plan_areas='user_input.plan_areas' if 'plan_areas' in body_keys else plan_areas,
        plan_transit='user_input.plan_transit' if 'plan_transit' in body_keys else plan_transit,
        plan_centers='user_input.plan_centers' if 'plan_centers' in body_keys else plan_centers,
        km2hm2=km2hm2
    ), outputFormat)
    