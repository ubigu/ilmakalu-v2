from typing import Annotated

from fastapi import APIRouter, Body, Query
from sqlmodel import SQLModel, text

from db import execute, get_table_name, insert_data, validate_years
from models.user_input import schema
from typings import UserInput

route = "co2-grid-processing"
router = APIRouter(
    prefix="/co2-grid-processing",
    tags=["CO2 Grid Processing"],
)


class __CommonParams(SQLModel):
    calculationYear: int
    baseYear: int
    mun: Annotated[list[int], Query()] = []
    aoi: str | None = None
    targetYear: int | None = None
    plan_areas: str | None = None
    plan_transit: str | None = None
    plan_centers: str | None = None
    km2hm2: float = 1.25
    outputFormat: str | None = None


def __run_query(p: Annotated[__CommonParams, Query()], body: dict | None = None):
    validate_years(p.baseYear, p.targetYear)
    stmt = text(
        """SELECT
            ST_AsText(geom) as geom, xyind,
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
    stmt = stmt.bindparams(
        municipalities=p.mun,
        aoi=f"{schema}.aoi" if body is not None and "aoi" in body.keys() else p.aoi,
        calculationYear=p.calculationYear,
        baseYear=p.baseYear,
        targetYear=p.targetYear,
        plan_areas=get_table_name(body, "plan_areas", p.plan_areas),
        plan_transit=get_table_name(body, "plan_transit", p.plan_transit),
        plan_centers=get_table_name(body, "plan_centers", p.plan_centers),
        km2hm2=p.km2hm2,
    )
    return execute(stmt, p.outputFormat)


@router.get(
    "/",
    responses={404: {"description": "Bad request"}},
)
def CO2_GridProcessing_get(params: Annotated[__CommonParams, Query()]):
    return __run_query(params)


@router.post(
    "/",
    responses={404: {"description": "Bad request"}},
)
def CO2_GridProcessing_post(params: Annotated[__CommonParams, Query()], body: Annotated[UserInput, Body()]):
    insert_data(body)
    return __run_query(params)
