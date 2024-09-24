from sqlmodel import SQLModel, Field, Index

schema = 'energy'

class cooling_gco2kwh(SQLModel, table=True):
    __table_args__ = (
        Index(
            "cooling_gco2kwh_index",
            "scenario",
            "year"
        ),
        { "schema": schema }
    )
    scenario: str = Field(primary_key=True)
    year: str = Field(primary_key=True)
    kaukok: int
    sahko: int
    pumput: int
    muu: int

class district_heating(SQLModel, table=True):
    __table_args__ = (
        Index(
            "district_heating_index",
            "scenario",
            "mun",
            "year"
        ),
        { "schema": schema }
    )
    mun: str = Field(primary_key=True)
    scenario: str = Field(primary_key=True)
    year: str = Field(primary_key=True)
    em: int
    hjm: int

class electricity(SQLModel, table=True):
    __table_args__ = (
        Index(
            "electricity_index",
            "scenario",
            "year"
        ),
        { "schema": schema }
    )
    scenario: str = Field(primary_key=True)
    year: str = Field(primary_key=True)
    metodi: str = Field(primary_key=True)
    paastolaji: str = Field(primary_key=True)
    gco2kwh: int

class electricity_home_percapita(SQLModel, table=True):
    __table_args__ = (
        Index(
            "electricity_home_percapita_index",
            "mun",
            "scenario",
            "year"
        ),
        { "schema": schema }
    )
    mun: str = Field(primary_key=True)
    scenario: str = Field(primary_key=True)
    year: str = Field(primary_key=True)
    sahko_koti_as: int

class heat_source_change(SQLModel, table=True):
    __table_args__ = (
        Index(
            "heat_source_change_index",
            "scenario",
            "rakennus_tyyppi"
        ),
        { "schema": schema }
    )
    scenario: str = Field(primary_key=True)
    rakennus_tyyppi: str = Field(primary_key=True)
    lammitysmuoto: str = Field(primary_key=True)
    kaukolampo: float
    kevyt_oljy: float
    kaasu: float
    sahko: float
    puu: float
    maalampo: float

class heating_degree_days(SQLModel, table=True):
    __table_args__ = (
        Index(
            "heating_degree_days_index",
            "mun"
        ),
        { "schema": schema }
    )
    mun: str = Field(primary_key=True)
    mun_name: str
    degreedays: int
    multiplier: float

class spaces_gco2kwh(SQLModel, table=True):
    __table_args__ = (
        Index(
            "spaces_gco2kwh_index",
            "vuosi"
        ),
        { "schema": schema }
    )
    vuosi: str = Field(primary_key=True)
    kaukolampo: int
    kevyt_oljy: int
    raskas_oljy: int
    kaasu: int
    sahko: int
    puu: int
    turve: int
    hiili: int
    maalampo: int
    muu_lammitys: int