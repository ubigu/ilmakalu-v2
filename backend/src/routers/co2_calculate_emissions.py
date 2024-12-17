from typing import Annotated, Literal

from fastapi import APIRouter, Body, Header, Query
from sqlmodel import SQLModel, text

from co2_query import CO2Query
from responses import responses
from typings import UserInput

router = APIRouter(prefix="/co2-calculate-emissions", tags=["CO2 Calculate Emissions"])


class CO2CalculateEmissions(CO2Query):
    def get_stmt(self):
        p = self.p
        return text(
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
                sum_liikenne_tco2, sum_sahko_tco2, sum_rakentaminen_tco2,
                sum_jatehuollon_paastot_tco2e
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
        ).bindparams(
            municipalities=p.mun,
            aoi=self.get_table_name("aoi", p.aoi),
            calculationYear=p.calculationYear,
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


class __CommonParams(SQLModel):
    calculationYear: int
    mun: Annotated[list[int], Query()] = []
    aoi: str | None = None
    calculationScenario: str = "wem"
    method: Literal["em", "hjm"] = "em"
    electricityType: Literal["hankinta", "tuotanto"] = "tuotanto"
    baseYear: int | None = None
    targetYear: int | None = None
    plan_areas: str | None = None
    plan_transit: str | None = None
    plan_centers: str | None = None
    includeLongDistance: bool = True
    includeBusinessTravel: bool = True
    outputFormat: str | None = None


class __CommonHeaders(SQLModel):
    uuid: str | None = None
    user: str | None = None


@router.get(
    "/",
    responses=responses,
)
def CO2_CalculateEmissions_get(
    params: Annotated[__CommonParams, Query()], headers: Annotated[__CommonHeaders, Header()]
):
    return CO2CalculateEmissions(params=params, headers=headers).execute()


@router.post(
    "/",
    responses=responses,
)
def CO2_CalculateEmissions_post(
    params: Annotated[__CommonParams, Query()],
    headers: Annotated[__CommonHeaders, Header()],
    body: Annotated[UserInput, Body()],
):
    return CO2CalculateEmissions(params=params, body=body, headers=headers).execute()
