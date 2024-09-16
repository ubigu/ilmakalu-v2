from database import Base
from sqlalchemy.orm import Mapped, mapped_column

schema = 'traffic'

class citizen_traffic_stress(Base):
    __tablename__ = "citizen_traffic_stress"
    __table_args__ = { 'schema': schema }
    mun: Mapped[str] = mapped_column(primary_key=True)
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    jalkapyora: Mapped[float] = mapped_column()
    bussi: Mapped[float] = mapped_column()
    raide: Mapped[float] = mapped_column()
    hlauto: Mapped[float] = mapped_column()
    muu: Mapped[float] = mapped_column()

class hlt_2015_tre(Base):
    __tablename__ = "hlt_2015_tre"
    __table_args__ = { 'schema': schema }
    zone: Mapped[int] = mapped_column(primary_key=True)
    jalkapyora: Mapped[float] = mapped_column()
    bussi: Mapped[float] = mapped_column()
    raide: Mapped[float] = mapped_column()
    hlauto: Mapped[float] = mapped_column()
    muu: Mapped[float] = mapped_column()

class hlt_kmchange(Base):
    __tablename__ = "hlt_kmchange"
    __table_args__ = { 'schema': schema }
    zone: Mapped[int] = mapped_column(primary_key=True)
    jalkapyora: Mapped[float] = mapped_column()
    bussi: Mapped[float] = mapped_column()
    raide: Mapped[float] = mapped_column()
    hlauto: Mapped[float] = mapped_column()
    muu: Mapped[float] = mapped_column()

class hlt_lookup(Base):
    __tablename__ = "hlt_lookup"
    __table_args__ = { 'schema': schema }
    mun: Mapped[str] = mapped_column(primary_key=True)
    hlt_table: Mapped[str] = mapped_column()

class hlt_workshare(Base):
    __tablename__ = "hlt_workshare"
    __table_args__ = { 'schema': schema }
    zone: Mapped[int] = mapped_column(primary_key=True)
    jalkapyora: Mapped[float] = mapped_column()
    bussi: Mapped[float] = mapped_column()
    raide: Mapped[float] = mapped_column()
    hlauto: Mapped[float] = mapped_column()
    muu: Mapped[float] = mapped_column()

class industr_performance(Base):
    __tablename__ = "industr_performance"
    __table_args__ = { 'schema': schema }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    kmuoto: Mapped[str] = mapped_column(primary_key=True)
    teoll_kaivos: Mapped[int] = mapped_column()
    teoll_elint: Mapped[int] = mapped_column()
    teoll_tekst: Mapped[int] = mapped_column()
    teoll_puu: Mapped[int] = mapped_column()
    teoll_paper: Mapped[int] = mapped_column()
    teoll_kemia: Mapped[int] = mapped_column()
    teoll_miner: Mapped[int] = mapped_column()
    teoll_mjalos: Mapped[int] = mapped_column()
    teoll_metal: Mapped[int] = mapped_column()
    teoll_kone: Mapped[int] = mapped_column()
    teoll_muu: Mapped[int] = mapped_column()
    teoll_energ: Mapped[int] = mapped_column()
    teoll_vesi: Mapped[int] = mapped_column()
    teoll_yhdysk: Mapped[int] = mapped_column()
    varast: Mapped[int] = mapped_column()
    teoll: Mapped[int] = mapped_column()

class industr_transport_km(Base):
    __tablename__ = "industr_transport_km"
    __table_args__ = { 'schema': schema }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    kmuoto: Mapped[str] = mapped_column(primary_key=True)
    teoll_kaivos: Mapped[int] = mapped_column()
    teoll_elint: Mapped[int] = mapped_column()
    teoll_tekst: Mapped[int] = mapped_column()
    teoll_puu: Mapped[int] = mapped_column()
    teoll_paper: Mapped[int] = mapped_column()
    teoll_kemia: Mapped[int] = mapped_column()
    teoll_miner: Mapped[int] = mapped_column()
    teoll_mjalos: Mapped[int] = mapped_column()
    teoll_metal: Mapped[int] = mapped_column()
    teoll_kone: Mapped[int] = mapped_column()
    teoll_muu: Mapped[int] = mapped_column()
    teoll_energ: Mapped[int] = mapped_column()
    teoll_vesi: Mapped[int] = mapped_column()
    teoll_yhdysk: Mapped[int] = mapped_column()
    varast: Mapped[int] = mapped_column()
    teoll: Mapped[int] = mapped_column()

class mode_power_distribution(Base):
    __tablename__ = "mode_power_distribution"
    __table_args__ = { 'schema': schema }
    mun: Mapped[str] = mapped_column(primary_key=True)
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    kmuoto: Mapped[str] = mapped_column(primary_key=True)
    kvoima_bensiini: Mapped[float] = mapped_column()
    kvoima_etanoli: Mapped[float] = mapped_column()
    kvoima_diesel: Mapped[float] = mapped_column()
    kvoima_kaasu: Mapped[float] = mapped_column()
    kvoima_phev_b: Mapped[float] = mapped_column()
    kvoima_phev_d: Mapped[float] = mapped_column()
    kvoima_ev: Mapped[float] = mapped_column()
    kvoima_vety: Mapped[float] = mapped_column()
    kvoima_muut: Mapped[float] = mapped_column()

class power_fossil_share(Base):
    __tablename__ = "power_fossil_share"
    __table_args__ = { 'schema': schema }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    share: Mapped[float] = mapped_column()

class power_kwhkm(Base):
    __tablename__ = "power_kwhkm"
    __table_args__ = { 'schema': schema }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    kmuoto: Mapped[str] = mapped_column(primary_key=True)
    kvoima_bensiini: Mapped[float] = mapped_column()
    kvoima_etanoli: Mapped[float] = mapped_column()
    kvoima_diesel: Mapped[float] = mapped_column()
    kvoima_kaasu: Mapped[float] = mapped_column()
    kvoima_phev_b: Mapped[float] = mapped_column()
    kvoima_phev_d: Mapped[float] = mapped_column()
    kvoima_ev: Mapped[float] = mapped_column()
    kvoima_vety: Mapped[float] = mapped_column()
    kvoima_muut: Mapped[float] = mapped_column()

class service_performance(Base):
    __tablename__ = "service_performance"
    __table_args__ = { 'schema': schema }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    kmuoto: Mapped[str] = mapped_column(primary_key=True)
    myymal_hyper: Mapped[float] = mapped_column()
    myymal_super: Mapped[float] = mapped_column()
    myymal_pien: Mapped[float] = mapped_column()
    myymal_muu: Mapped[float] = mapped_column()
    majoit: Mapped[float] = mapped_column()
    asla: Mapped[float] = mapped_column()
    ravint: Mapped[float] = mapped_column()
    tsto: Mapped[float] = mapped_column()
    liiken: Mapped[float] = mapped_column()
    hoito: Mapped[float] = mapped_column()
    kokoon: Mapped[float] = mapped_column()
    opetus: Mapped[float] = mapped_column()
    muut: Mapped[float] = mapped_column()

class services_transport_km(Base):
    __tablename__ = "services_transport_km"
    __table_args__ = { 'schema': schema }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    kmuoto: Mapped[str] = mapped_column(primary_key=True)
    myymal_hyper: Mapped[int] = mapped_column()
    myymal_super: Mapped[int] = mapped_column()
    myymal_pien: Mapped[int] = mapped_column()
    myymal_muu: Mapped[int] = mapped_column()
    majoit: Mapped[int] = mapped_column()
    asla: Mapped[int] = mapped_column()
    ravint: Mapped[int] = mapped_column()
    tsto: Mapped[int] = mapped_column()
    liiken: Mapped[int] = mapped_column()
    hoito: Mapped[int] = mapped_column()
    kokoon: Mapped[int] = mapped_column()
    opetus: Mapped[int] = mapped_column()
    muut: Mapped[int] = mapped_column()

class workers_traffic_stress(Base):
    __tablename__ = "workers_traffic_stress"
    __table_args__ = { 'schema': schema }
    mun: Mapped[str] = mapped_column(primary_key=True)
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    jalkapyora: Mapped[float] = mapped_column()
    bussi: Mapped[float] = mapped_column()
    raide: Mapped[float] = mapped_column()
    hlauto: Mapped[float] = mapped_column()
    muu: Mapped[float] = mapped_column()