from typing import Annotated, Literal, NotRequired, TypedDict

from fastapi import Body, Header, Query
from sqlmodel import SQLModel


class __CO2Params(SQLModel):
    mun: Annotated[list[int], Query()] = []
    aoi: str | None = None
    plan_areas: str | None = None
    plan_transit: str | None = None
    plan_centers: str | None = None
    outputFormat: str | None = None


class __CO2CalculateEmissionsParamsBase(__CO2Params):
    calculationScenario: str = "wem"
    method: Literal["em", "hjm"] = "em"
    electricityType: Literal["hankinta", "tuotanto"] = "tuotanto"
    includeLongDistance: bool = True
    includeBusinessTravel: bool = True
    writeSessionInfo: bool | None = None


class __CO2GridProcessingParams(__CO2Params):
    calculationYear: int
    baseYear: int
    targetYear: int | None = None
    km2hm2: float = 1.25


CO2GridProcessingParams = Annotated[__CO2GridProcessingParams, Query()]


class __CO2CalculateEmissionsParams(__CO2CalculateEmissionsParamsBase):
    calculationYear: int
    baseYear: int | None = None
    targetYear: int | None = None


CO2CalculateEmissionsParams = Annotated[__CO2CalculateEmissionsParams, Query()]


class __CO2CalculateEmissionsLoopParams(__CO2CalculateEmissionsParamsBase):
    baseYear: int
    targetYear: int


CO2CalculateEmissionsLoopParams = Annotated[__CO2CalculateEmissionsLoopParams, Query()]


class __CO2Headers(SQLModel):
    uuid: str | None = None
    user: str | None = None


CO2Headers = Annotated[__CO2Headers, Header()]


class __CO2Body(TypedDict):
    layers: NotRequired[str]
    connParams: NotRequired[str]


CO2Body = Annotated[__CO2Body, Body()]


class CO2Result(TypedDict):
    geom: str
    xyind: str
    mun: int
    zone: int
    pop: int
    employ: int
    maa_ha: NotRequired[float]
    centdist: NotRequired[int]
    alueteho: NotRequired[float]
    k_ap_ala: NotRequired[int]
    k_ar_ala: NotRequired[int]
    k_ak_ala: NotRequired[int]
    k_muu_ala: NotRequired[int]
    k_poistuma: NotRequired[int]
    holidayhouses: NotRequired[int]
    year: NotRequired[int]
    floorspace: NotRequired[int]
    tilat_vesi_tco2: NotRequired[float]
    tilat_lammitys_tco2: NotRequired[float]
    tilat_jaahdytys_tco2: NotRequired[float]
    sahko_kiinteistot_tco2: NotRequired[float]
    sahko_kotitaloudet_tco2: NotRequired[float]
    sahko_palv_tco2: NotRequired[float]
    sahko_tv_tco2: NotRequired[float]
    liikenne_as_tco2: NotRequired[float]
    liikenne_tp_tco2: NotRequired[float]
    liikenne_tv_tco2: NotRequired[float]
    liikenne_palv_tco2: NotRequired[float]
    rak_korjaussaneeraus_tco2: NotRequired[float]
    rak_purku_tco2: NotRequired[float]
    rak_uudis_tco2: NotRequired[float]
    sum_yhteensa_tco2: NotRequired[float]
    sum_lammonsaato_tco2: NotRequired[float]
    sum_liikenne_tco2: NotRequired[float]
    sum_sahko_tco2: NotRequired[float]
    sum_rakentaminen_tco2: NotRequired[float]
