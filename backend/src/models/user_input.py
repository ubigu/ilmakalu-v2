from sqlmodel import SQLModel, Field
from geoalchemy2 import Geometry
from sqlalchemy.dialects.postgresql import VARCHAR

schema = 'user_input'

class plan_areas_base(SQLModel):
    __table_args__ = { "schema": schema }
    geom: object = Field(sa_type=Geometry('MULTIPOLYGON'))
    id: int | None = Field(default=None, primary_key=True)
    k_ap_ala: int | None = None
    k_ar_ala: int | None = None
    k_ak_ala: int | None = None
    k_muu_ala: int | None = None
    k_poistuma: int | None = None
    k_tp_yht: int | None = None
    k_aloitusv: int | None = None
    k_valmisv: int | None = None
    kem2: int | None = None
    year_completion: int | None = None
    type: int | None = None

class plan_transit_base(SQLModel):
    __table_args__ = { "schema": schema }
    geom: object = Field(sa_type=Geometry('POINT'))
    id: int | None = Field(default=None, primary_key=True)
    k_jltyyp: str | None = Field(default=None)
    k_jlnimi: str | None = Field(sa_type=VARCHAR(50), default=None)
    k_liikv: int

class plan_centers_base(SQLModel):
    __table_args__ = { "schema": schema }
    geom: object = Field(sa_type=Geometry('POINT'),primary_key=True)
    k_ktyyp: str
    k_knimi: str = Field(sa_type=VARCHAR(50))
    k_kalkuv: int | None = None
    k_kvalmv: int | None = None

class aoi_base(SQLModel):
    __table_args__ = { "schema": schema }
    geom: object = Field(sa_type=Geometry(),primary_key=True)


