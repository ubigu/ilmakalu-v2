from typing import cast

from fastapi import APIRouter
from sqlmodel import text

from co2_query import CO2Query
from ilmakalu_typing import CO2Body, CO2GridProcessingParams
from responses import responses

router = APIRouter(
    prefix="/co2-grid-processing",
    tags=["CO2 Grid Processing"],
)


class CO2GridProcessing(CO2Query):
    def get_stmt(self):
        p = cast(CO2GridProcessingParams, self.params)
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
            municipalities=p.mun,
            aoi=self.get_table_name("aoi", p.aoi),
            calculationYear=p.calculationYear,
            baseYear=p.baseYear,
            targetYear=p.targetYear,
            plan_areas=self.get_table_name("plan_areas", p.plan_areas),
            plan_transit=self.get_table_name("plan_transit", p.plan_transit),
            plan_centers=self.get_table_name("plan_centers", p.plan_centers),
            km2hm2=p.km2hm2,
        )


@router.get(
    "/",
    responses=responses,
)
def CO2_GridProcessing_get(params: CO2GridProcessingParams):
    return CO2GridProcessing(params=params).execute()


@router.post(
    "/",
    responses=responses,
)
def CO2_GridProcessing_post(params: CO2GridProcessingParams, body: CO2Body):
    return CO2GridProcessing(params=params, body=body).execute()
