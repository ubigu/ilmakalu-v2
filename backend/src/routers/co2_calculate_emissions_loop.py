from typing import cast

from fastapi import APIRouter
from sqlmodel import text

from co2_query import CO2CalculateEmissionsBase
from ilmakalu_typing import CO2Body, CO2CalculateEmissionsLoopParams, CO2Headers
from responses import responses

router = APIRouter(
    prefix="/co2-calculate-emissions-loop",
    tags=["CO2 Calculate Emissions Loop"],
)


class CO2CalculateEmissionsLoop(CO2CalculateEmissionsBase):
    def get_stmt(self):
        p = cast(CO2CalculateEmissionsLoopParams, self.params)
        return text(
            """SELECT
                ST_AsText(geom) as geom, xyind, mun, zone, holidayhouses,
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
        ).bindparams(
            municipalities=p.mun,
            aoi=self.get_table_name("aoi", p.aoi),
            calculationScenario=p.calculationScenario,
            method=p.method,
            electricityType=p.electricityType,
            baseYear=p.baseYear,
            targetYear=p.targetYear,
            plan_areas=self.get_table_name("plan_areas", p.plan_areas),
            plan_transit=self.get_table_name("plan_transit", p.plan_transit),
            plan_centers=self.get_table_name("plan_centers", p.plan_centers),
            includeLongDistance=p.includeLongDistance,
            includeBusinessTravel=p.includeBusinessTravel,
        )


@router.get(
    "/",
    responses=responses,
)
def CO2_CalculateEmissionsLoop_get(params: CO2CalculateEmissionsLoopParams, headers: CO2Headers):
    return CO2CalculateEmissionsLoop(params=params, headers=headers).execute()


@router.post(
    "/",
    responses=responses,
)
def CO2_CalculateEmissionsLoop_post(
    params: CO2CalculateEmissionsLoopParams,
    headers: CO2Headers,
    body: CO2Body,
):
    return CO2CalculateEmissionsLoop(params=params, body=body, headers=headers).execute()
