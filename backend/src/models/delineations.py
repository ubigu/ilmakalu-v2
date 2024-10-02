from sqlmodel import SQLModel, Field
from geoalchemy2 import Geometry
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import VARCHAR, BIGINT, SMALLINT

schema = 'delineations'

class centroids(SQLModel, table=True):
    __table_args__ = { "schema": schema }
    geom: object = Field(sa_column=Column(Geometry('POINT')))
    id: int = Field(primary_key=True)
    keskustyyp: str = Field(sa_column=Column(VARCHAR(50)))
    keskusnimi: str = Field(sa_column=Column(VARCHAR(50)))

class grid(SQLModel, table=True):
    __table_args__ = { "schema": schema }
    geom: object = Field(sa_column=Column(Geometry('MULTIPOLYGON')))
    xyind: str = Field(sa_column=Column(VARCHAR(13), primary_key=True))
    mun: int
    zone: int = Field(sa_column=Column(BIGINT))
    centdist: int = Field(sa_column=Column(SMALLINT))