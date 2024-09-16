from database import Base
from sqlalchemy.orm import Mapped, mapped_column

schema = 'energy'

class cooling_gco2kwh(Base):
    __tablename__ = "cooling_gco2kwh"
    __table_args__ = { 'schema': schema }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    kaukok: Mapped[int] = mapped_column()
    sahko: Mapped[int] = mapped_column()
    pumput: Mapped[int] = mapped_column()
    muu: Mapped[int] = mapped_column()

class district_heating(Base):
    __tablename__ = "district_heating"
    __table_args__ = { 'schema': schema }
    mun: Mapped[str] = mapped_column(primary_key=True)
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    em: Mapped[int] = mapped_column()
    hjm: Mapped[int] = mapped_column()

class electricity(Base):
    __tablename__ = "electricity"
    __table_args__ = { 'schema': schema }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    metodi: Mapped[str] = mapped_column(primary_key=True)
    paastolaji: Mapped[str] = mapped_column(primary_key=True)
    gco2kwh: Mapped[int] = mapped_column()

class electricity_home_percapita(Base):
    __tablename__ = "electricity_home_percapita"
    __table_args__ = { 'schema': schema }
    mun: Mapped[str] = mapped_column(primary_key=True)
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    sahko_koti_as: Mapped[int] = mapped_column()

class heat_source_change(Base):
    __tablename__ = "heat_source_change"
    __table_args__ = { 'schema': schema }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    rakennus_tyyppi: Mapped[str] = mapped_column(primary_key=True)
    lammitysmuoto: Mapped[str] = mapped_column(primary_key=True)
    kaukolampo: Mapped[float] = mapped_column()
    kevyt_oljy: Mapped[float] = mapped_column()
    kaasu: Mapped[float] = mapped_column()
    sahko: Mapped[float] = mapped_column()
    puu: Mapped[float] = mapped_column()
    maalampo: Mapped[float] = mapped_column()

class heating_degree_days(Base):
    __tablename__ = "heating_degree_days"
    __table_args__ = { 'schema': schema }
    mun: Mapped[str] = mapped_column(primary_key=True)
    mun_name: Mapped[str] = mapped_column()
    degreedays: Mapped[int] = mapped_column()
    multiplier: Mapped[float] = mapped_column()

class spaces_gco2kwh(Base):
    __tablename__ = "spaces_gco2kwh"
    __table_args__ = { 'schema': schema }
    vuosi: Mapped[int] = mapped_column(primary_key=True)
    kaukolampo: Mapped[int] = mapped_column()
    kevyt_oljy: Mapped[int] = mapped_column()
    raskas_oljy: Mapped[int] = mapped_column()
    kaasu: Mapped[int] = mapped_column()
    sahko: Mapped[int] = mapped_column()
    puu: Mapped[int] = mapped_column()
    turve: Mapped[int] = mapped_column()
    hiili: Mapped[int] = mapped_column()
    maalampo: Mapped[int] = mapped_column()
    muu_lammitys: Mapped[int] = mapped_column()