from sqlmodel import SQLModel, Field, Index
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import REAL

schema = 'built'

class build_demolish_energy_gco2m2(SQLModel, table=True):
    __table_args__ = (
        Index(
            "build_demolish_index",
            "scenario",
            "year"
        ),
        { "schema": schema }
    )
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
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

class build_materia_gco2m2(SQLModel, table=True):
    __table_args__ = (
        Index(
            "build_materia_index",
            "scenario",
            "year"
        ),
        { "schema": schema }
    )
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
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

class build_new_construction_energy_gco2m2(SQLModel, table=True):
    __table_args__ = (
        Index(
            "construction_index",
            "scenario",
            "year"
        ),
        { "schema": schema }
    )
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
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

class build_rebuilding_energy_gco2m2(SQLModel, table=True):
    __table_args__ = (
        Index(
            "build_rebuilding_energy_index",
            "scenario",
            "year"
        ),
        { "schema": schema }
    )
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
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

class build_rebuilding_share(SQLModel, table=True):
    __table_args__ = (
        Index(
            "build_rebuilding_share_index",
            "scenario",
            "year",
            "rakv"
        ),
        { "schema": schema }
    )
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
    __table_args__ = (
        Index(
            "build_renovation_energy_index",
            "scenario",
            "year"
        ),
        { "schema": schema }
    )
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
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

class cooling_proportions_kwhm2(SQLModel, table=True):
    __table_args__ = (
        Index(
            "cooling_proportions_index",
            "scenario",
            "rakv"
        ),
        { "schema": schema }
    )
    scenario: str = Field(primary_key=True)
    rakv: int = Field(primary_key=True)
    rakennus_tyyppi: str = Field(primary_key=True)
    jaahdytys_osuus: float
    jaahdytys_kwhm2: float
    jaahdytys_kaukok: float
    jaahdytys_sahko: float
    jaahdytys_pumput: float
    jaahdytys_muu: float


class distribution_heating_systems(SQLModel, table=True):
    __table_args__ = (
        Index(
            "distribution_heating_system_index",
            "scenario",
            "year",
            "rakv",
            "rakennus_tyyppi"
        ),
        { "schema": schema }
    )
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
    __table_args__ = (
        Index(
            "electricity_home_device_index",
            "scenario",
            "year"
        ),
        { "schema": schema }
    )
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    erpien: float
    rivita: float
    askert: float

class electricity_home_light(SQLModel, table=True):
    __table_args__ = (
        Index(
            "electricity_home_light_index",
            "scenario",
            "year"
        ),
        { "schema": schema }
    )
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    erpien: float
    rivita: float
    askert: float

class electricity_iwhs_kwhm2(SQLModel, table=True):
    __table_args__ = (
        Index(
            "electricity_industry_index",
            "scenario",
            "year"
        ),
        { "schema": schema }
    )
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    myymal_hyper: float
    myymal_super: float
    myymal_pien: float
    myymal_muu: float
    majoit: float
    asla: float
    ravint: float
    tsto: float
    liiken: float
    hoito: float
    kokoon: float
    opetus: float
    muut: float
    teoll_kaivos: float
    teoll_elint: float
    teoll_tekst: float
    teoll_puu: float
    teoll_paper: float
    teoll_kemia: float
    teoll_miner: float
    teoll_mjalos: float
    teoll_metal: float
    teoll_kone: float
    teoll_muu: float
    teoll_energ: float
    teoll_vesi: float
    teoll_yhdysk: float
    varast: float
    teoll: float
    liike: float
    myymal: float

class electricity_property_change(SQLModel, table=True):
    __table_args__ = (
        Index(
            "electricity_property_change_index",
            "scenario",
            "year"
        ),
        { "schema": schema }
    )
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    c_9999: float = Field(sa_column_kwargs={'name': '9999'})
    c_1920: float = Field(sa_column_kwargs={'name': '1920'})
    c_1929: float = Field(sa_column_kwargs={'name': '1929'})
    c_1939: float = Field(sa_column_kwargs={'name': '1939'})
    c_1949: float = Field(sa_column_kwargs={'name': '1949'})
    c_1959: float = Field(sa_column_kwargs={'name': '1959'})
    c_1969: float = Field(sa_column_kwargs={'name': '1969'})
    c_1979: float = Field(sa_column_kwargs={'name': '1979'})
    c_1989: float = Field(sa_column_kwargs={'name': '1989'})
    c_1999: float = Field(sa_column_kwargs={'name': '1999'})
    c_2009: float = Field(sa_column_kwargs={'name': '2009'})
    c_2010: float = Field(sa_column_kwargs={'name': '2010'})

class electricity_property_kwhm2(SQLModel, table=True):
    __table_args__ = (
        Index(
            "electricity_property_kwhkm_index",
            "scenario",
            "rakv"
        ),
        { "schema": schema }
    )
    scenario: str = Field(primary_key=True)
    rakv: int = Field(primary_key=True)
    rakennus_tyyppi: str = Field(primary_key=True)
    sahko_kiinteisto_kwhm2: float

class iwhs_sizes(SQLModel, table=True):
    __table_args__ = { "schema": schema }
    type: str = Field(primary_key=True)
    several: int
    single: int

class occupancy(SQLModel, table=True):
    __table_args__ = (
        Index(
            "occupancy_index",
            "mun",
            "year"
        ),
        { "schema": schema }
    )
    mun: int = Field(primary_key=True)
    year: int = Field(primary_key=True)
    erpien: float = Field(sa_column=Column(REAL))
    rivita: float = Field(sa_column=Column(REAL))
    askert: float = Field(sa_column=Column(REAL))

class spaces_efficiency(SQLModel, table=True):
    __table_args__ = (
        Index(
            "spaces_efficiency_index",
            "scenario",
            "rakv",
            "rakennus_tyyppi"
        ),
        { "schema": schema }
    )
    scenario: str = Field(primary_key=True)
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
    __table_args__ = (
        Index(
            "spaces_kwhm2_index",
            "scenario",
            "rakv",
            "year"
        ),
        { "schema": schema }
    )
    mun: int = Field(primary_key=True)
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

class water_kwhm2(SQLModel, table=True):
    __table_args__ = (
        Index(
            "water_kwhm2_index",
            "scenario",
            "rakv",
            "rakennus_tyyppi"
        ),
        { "schema": schema }
    )
    scenario: str = Field(primary_key=True)
    rakv: int = Field(primary_key=True)
    rakennus_tyyppi: str = Field(primary_key=True)
    vesi_kwh_m2: float