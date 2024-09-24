from sqlmodel import SQLModel, Field, Index

schema = 'traffic'

class citizen_traffic_stress(SQLModel, table=True):
    __table_args__ = (
        Index(
            "personal_traffic_index",
            "mun",
            "scenario",
            "year"
        ),
        { "schema": schema }
    )
    mun: str = Field(primary_key=True)
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    jalkapyora: float
    bussi: float
    raide: float
    hlauto: float
    muu: float

class hlt_2015_tre(SQLModel, table=True):
    __table_args__ = { "schema": schema }
    zone: int = Field(primary_key=True)
    jalkapyora: float
    bussi: float
    raide: float
    hlauto: float
    muu: float

class hlt_kmchange(SQLModel, table=True):
    __table_args__ = { "schema": schema }
    zone: int = Field(primary_key=True)
    jalkapyora: float
    bussi: float
    raide: float
    hlauto: float
    muu: float

class hlt_lookup(SQLModel, table=True):
    __table_args__ = { "schema": schema }
    mun: str = Field(primary_key=True)
    hlt_table: str

class hlt_workshare(SQLModel, table=True):
    __table_args__ = { "schema": schema }
    zone: int = Field(primary_key=True)
    jalkapyora: float
    bussi: float
    raide: float
    hlauto: float
    muu: float

class industr_performance(SQLModel, table=True):
    __table_args__ = (
        Index(
            "industry_performance_index",
            "scenario",
            "year",
            "kmuoto"
        ),
        { "schema": schema }
    )
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    kmuoto: str = Field(primary_key=True)
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

class industr_transport_km(SQLModel, table=True):
    __table_args__ = (
        Index(
            "industry_performance_km_index",
            "scenario",
            "year",
            "kmuoto"
        ),
        { "schema": schema }
    )
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    kmuoto: str = Field(primary_key=True)
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

class mode_power_distribution(SQLModel, table=True):
    __table_args__ = (
        Index(
            "mode_power_distribution_index",
            "scenario",
            "year",
            "kmuoto"
        ),
        { "schema": schema }
    )
    mun: str = Field(primary_key=True)
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    kmuoto: str = Field(primary_key=True)
    kvoima_bensiini: float
    kvoima_etanoli: float
    kvoima_diesel: float
    kvoima_kaasu: float
    kvoima_phev_b: float
    kvoima_phev_d: float
    kvoima_ev: float
    kvoima_vety: float
    kvoima_muut: float

class power_fossil_share(SQLModel, table=True):
    __table_args__ = (
        Index(
            "power_fossil_share_index",
            "scenario",
            "year"
        ),
        { "schema": schema }
    )
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    share: float

class power_kwhkm(SQLModel, table=True):
    __table_args__ = (
        Index(
            "power_kwhkm_index",
            "scenario",
            "year",
            "kmuoto"
        ),
        { "schema": schema }
    )
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    kmuoto: str = Field(primary_key=True)
    kvoima_bensiini: float
    kvoima_etanoli: float
    kvoima_diesel: float
    kvoima_kaasu: float
    kvoima_phev_b: float
    kvoima_phev_d: float
    kvoima_ev: float
    kvoima_vety: float
    kvoima_muut: float

class service_performance(SQLModel, table=True):
    __table_args__ = (
        Index(
            "service_performance_index",
            "scenario",
            "year",
            "kmuoto"
        ),
        { "schema": schema }
    )
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    kmuoto: str = Field(primary_key=True)
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

class services_transport_km(SQLModel, table=True):
    __table_args__ = (
        Index(
            "service_transport_index",
            "scenario",
            "year",
            "kmuoto"
        ),
        { "schema": schema }
    )
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    kmuoto: str = Field(primary_key=True)
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

class workers_traffic_stress(SQLModel, table=True):
    __table_args__ = (
        Index(
            "workers_traffic_stress_index",
            "mun",
            "scenario",
            "year"
        ),
        { "schema": schema }
    )
    mun: str = Field(primary_key=True)
    scenario: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    jalkapyora: float
    bussi: float
    raide: float
    hlauto: float
    muu: float