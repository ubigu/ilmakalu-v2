from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import REAL
from sqlmodel import Field, SQLModel

"""SQLModel models for the schema 'built'"""

schema = "built"


class build_demolish_energy_gco2m2(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    erpien: int
    rivita: int
    askert: int
    liike: int
    tsto: int
    liiken: int
    hoito: int
    kokoon: int
    opetus: int
    teoll: int
    varast: int
    muut: int


class build_materia_gco2m2(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    erpien: int
    rivita: int
    askert: int
    liike: int
    tsto: int
    liiken: int
    hoito: int
    kokoon: int
    opetus: int
    teoll: int
    varast: int
    muut: int


class build_new_construction_energy_gco2m2(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    erpien: int
    rivita: int
    askert: int
    liike: int
    tsto: int
    liiken: int
    hoito: int
    kokoon: int
    opetus: int
    teoll: int
    varast: int
    muut: int


class build_rebuilding_energy_gco2m2(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    erpien: int
    rivita: int
    askert: int
    liike: int
    tsto: int
    liiken: int
    hoito: int
    kokoon: int
    opetus: int
    teoll: int
    varast: int
    muut: int


class build_rebuilding_share(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    rakv: int = Field(primary_key=True)
    erpien: float
    rivita: float
    askert: float
    liike: float
    tsto: float
    liiken: float
    hoito: float
    kokoon: float
    opetus: float
    teoll: float
    varast: float
    muut: float


class build_renovation_energy_gco2m2(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    erpien: int
    rivita: int
    askert: int
    liike: int
    tsto: int
    liiken: int
    hoito: int
    kokoon: int
    opetus: int
    teoll: int
    varast: int
    muut: int


class cooling_proportions_kwhm2(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    scenario: str = Field(primary_key=True)
    rakv: int = Field(primary_key=True)
    rakennus_tyyppi: str = Field(primary_key=True)
    jaahdytys_osuus: int
    jaahdytys_kwhm2: float
    jaahdytys_kaukok: float
    jaahdytys_sahko: float
    jaahdytys_pumput: float
    jaahdytys_muu: float


class distribution_heating_systems(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    rakv: int = Field(primary_key=True)
    rakennus_tyyppi: str = Field(primary_key=True)
    kaukolampo: float
    kevyt_oljy: float
    kaasu: float
    sahko: float
    puu: float
    maalampo: float
    muu_lammitys: float


class electricity_home_device(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    erpien: float
    rivita: float
    askert: float


class electricity_home_light(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    erpien: float
    rivita: float
    askert: float


class electricity_iwhs_kwhm2(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    mun: int = Field(primary_key=True)
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    myymal_hyper: int
    myymal_super: int
    myymal_pien: int
    myymal_muu: int
    majoit: int
    asla: int
    ravint: int
    tsto: int
    liiken: int
    hoito: int
    kokoon: int
    opetus: int
    muut: int
    teoll_kaivos: int
    teoll_elint: int
    teoll_tekst: int
    teoll_puu: int
    teoll_paper: int
    teoll_kemia: int
    teoll_miner: int
    teoll_mjalos: int
    teoll_metal: int
    teoll_kone: int
    teoll_muu: int
    teoll_energ: int
    teoll_vesi: int
    teoll_yhdysk: int
    varast: int
    teoll: int
    liike: int
    myymal: int


class electricity_property_change(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    c_9999: float = Field(sa_column_kwargs={"name": "9999"})
    c_1920: float = Field(sa_column_kwargs={"name": "1920"})
    c_1929: float = Field(sa_column_kwargs={"name": "1929"})
    c_1939: float = Field(sa_column_kwargs={"name": "1939"})
    c_1949: float = Field(sa_column_kwargs={"name": "1949"})
    c_1959: float = Field(sa_column_kwargs={"name": "1959"})
    c_1969: float = Field(sa_column_kwargs={"name": "1969"})
    c_1979: float = Field(sa_column_kwargs={"name": "1979"})
    c_1989: float = Field(sa_column_kwargs={"name": "1989"})
    c_1999: float = Field(sa_column_kwargs={"name": "1999"})
    c_2009: float = Field(sa_column_kwargs={"name": "2009"})
    c_2010: float = Field(sa_column_kwargs={"name": "2010"})


class electricity_property_kwhm2(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    scenario: str = Field(primary_key=True)
    rakv: int = Field(primary_key=True)
    rakennus_tyyppi: str = Field(primary_key=True)
    sahko_kiinteisto_kwhm2: float


class iwhs_sizes(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    type: str = Field(primary_key=True)
    several: int
    single: int


class occupancy(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    mun: int = Field(primary_key=True)
    year: int = Field(primary_key=True)
    erpien: float = Field(sa_column=Column(REAL))
    rivita: float = Field(sa_column=Column(REAL))
    askert: float = Field(sa_column=Column(REAL))


class spaces_efficiency(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    rakv: int = Field(primary_key=True)
    rakennus_tyyppi: str = Field(primary_key=True)
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


class spaces_kwhm2(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    mun: int = Field(primary_key=True)
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    rakv: int = Field(primary_key=True)
    erpien: int
    rivita: int
    askert: int
    liike: int
    tsto: int
    liiken: int
    hoito: int
    kokoon: int
    opetus: int
    teoll: int
    varast: int
    muut: int


class water_kwhm2(SQLModel, table=True):
    __table_args__ = {"schema": schema}
    scenario: str = Field(primary_key=True)
    rakv: int = Field(primary_key=True)
    rakennus_tyyppi: str = Field(primary_key=True)
    vesi_kwh_m2: int
