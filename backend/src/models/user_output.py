from sqlalchemy import Column, Integer
from sqlalchemy.dialects.postgresql import ARRAY, VARCHAR
from sqlmodel import Field, SQLModel

schema = "user_output"


class sessions(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    uuid: str = Field(sa_column=Column(VARCHAR(36), primary_key=True))
    user: str
    startTime: str = Field(sa_column=Column(VARCHAR(15), primary_key=True))
    baseYear: int
    targetYear: int | None
    calculationScenario: str
    method: str
    electricityType: str
    geomArea: list[int] = Field(sa_column=Column(ARRAY(Integer)))
