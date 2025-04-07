from sqlmodel import Field, SQLModel

"""SQLModel models for the schema 'energy'"""

schema = "energy"


class cooling_gco2kwh(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    kaukok: int
    sahko: int
    pumput: int
    muu: int


class district_heating(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    mun: int = Field(primary_key=True)
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    gco2kwh: float


class electricity(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    gco2kwh: float


class electricity_home_percapita(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    mun: int = Field(primary_key=True)
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    sahko_koti_as: int


class heat_source_change(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    scenario: str = Field(primary_key=True)
    rakennus_tyyppi: str = Field(primary_key=True)
    lammitysmuoto: str = Field(primary_key=True)
    kaukolampo: float
    kevyt_oljy: float
    raskas_oljy: float
    kaasu: float
    sahko: float
    puu: float
    turve: float
    hiili: float
    maalampo: float
    muu_lammitys: float


class heating_degree_days(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    mun: int = Field(primary_key=True)
    year: int = Field(primary_key=True)
    degreedays: int


class spaces_gco2kwh(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    year: int = Field(primary_key=True)
    kevyt_oljy: int
    kaasu: int
    puu: int
    muu_lammitys: int
