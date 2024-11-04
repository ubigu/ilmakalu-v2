from typing import Annotated

from fastapi import APIRouter, Body, Query
from sqlmodel import SQLModel, text

from co2_query import CO2Query
from responses import responses
from typings import UserInput

route = "co2-grid-processing"
router = APIRouter(
    prefix="/co2-grid-processing",
    tags=["CO2 Grid Processing"],
)


class CO2GridProcessing(CO2Query):
    def get_stmt(self):
        return text(
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
        ).bindparams(
            municipalities=self.p.mun,
            aoi=self.get_table_name("aoi", self.p.aoi),
            calculationYear=self.p.calculationYear,
            baseYear=self.p.baseYear,
            targetYear=self.p.targetYear,
            plan_areas=self.get_table_name("plan_areas", self.p.plan_areas),
            plan_transit=self.get_table_name("plan_transit", self.p.plan_transit),
            plan_centers=self.get_table_name("plan_centers", self.p.plan_centers),
            km2hm2=self.p.km2hm2,
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


@router.get(
    "/",
    responses=responses,
)
def CO2_GridProcessing_get(params: Annotated[__CommonParams, Query()]):
    return CO2GridProcessing(params=params).execute()


@router.post(
    "/",
    responses=responses,
)
def CO2_GridProcessing_post(params: Annotated[__CommonParams, Query()], body: Annotated[UserInput, Body()]):
    return CO2GridProcessing(params=params, body=body).execute()
