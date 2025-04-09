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
    writeSessionInfo: bool | None = None


class __CO2CalculateEmissionsParamsBase(__CO2Params):
    calculationScenario: Literal["wemp", "wemh", "weml", "static"] = "wemp"
    includeLongDistance: bool = True
    includeBusinessTravel: bool = True


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
