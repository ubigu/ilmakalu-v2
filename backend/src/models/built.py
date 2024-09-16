from database import Base
from sqlalchemy.orm import Mapped, mapped_column

schema = 'built'

class build_demolish_energy_gco2m2(Base):
    __tablename__ = "build_demolish_energy_gco2m2"
    __table_args__ = { "schema": schema }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    erpien: Mapped[float] = mapped_column()
    rivita: Mapped[float] = mapped_column()
    askert: Mapped[float] = mapped_column()
    liike: Mapped[float] = mapped_column()
    tsto: Mapped[float] = mapped_column()
    liiken: Mapped[float] = mapped_column()
    hoito: Mapped[float] = mapped_column()
    kokoon: Mapped[float] = mapped_column()
    opetus: Mapped[float] = mapped_column()
    teoll: Mapped[float] = mapped_column()
    varast: Mapped[float] = mapped_column()
    muut: Mapped[float] = mapped_column()

class build_materia_gco2m2(Base):
    __tablename__ = "build_materia_gco2m2"
    __table_args__ = { 'schema': schema }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    erpien: Mapped[float] = mapped_column()
    rivita: Mapped[float] = mapped_column()
    askert: Mapped[float] = mapped_column()
    liike: Mapped[float] = mapped_column()
    tsto: Mapped[float] = mapped_column()
    liiken: Mapped[float] = mapped_column()
    hoito: Mapped[float] = mapped_column()
    kokoon: Mapped[float] = mapped_column()
    opetus: Mapped[float] = mapped_column()
    teoll: Mapped[float] = mapped_column()
    varast: Mapped[float] = mapped_column()
    muut: Mapped[float] = mapped_column()

class build_new_construction_energy_gco2m2(Base):
    __tablename__ = "build_new_construction_energy_gco2m2"
    __table_args__ = { 'schema': schema }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    erpien: Mapped[float] = mapped_column()
    rivita: Mapped[float] = mapped_column()
    askert: Mapped[float] = mapped_column()
    liike: Mapped[float] = mapped_column()
    tsto: Mapped[float] = mapped_column()
    liiken: Mapped[float] = mapped_column()
    hoito: Mapped[float] = mapped_column()
    kokoon: Mapped[float] = mapped_column()
    opetus: Mapped[float] = mapped_column()
    teoll: Mapped[float] = mapped_column()
    varast: Mapped[float] = mapped_column()
    muut: Mapped[float] = mapped_column()

class build_rebuilding_energy_gco2m2(Base):
    __tablename__ = "build_rebuilding_energy_gco2m2"
    __table_args__ = { 'schema': schema }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    erpien: Mapped[float] = mapped_column()
    rivita: Mapped[float] = mapped_column()
    askert: Mapped[float] = mapped_column()
    liike: Mapped[float] = mapped_column()
    tsto: Mapped[float] = mapped_column()
    liiken: Mapped[float] = mapped_column()
    hoito: Mapped[float] = mapped_column()
    kokoon: Mapped[float] = mapped_column()
    opetus: Mapped[float] = mapped_column()
    teoll: Mapped[float] = mapped_column()
    varast: Mapped[float] = mapped_column()
    muut: Mapped[float] = mapped_column()

class build_rebuilding_share(Base):
    __tablename__ = "build_rebuilding_share"
    __table_args__ = { 'schema': schema }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    rakv: Mapped[int] = mapped_column(primary_key=True)
    erpien: Mapped[float] = mapped_column()
    rivita: Mapped[float] = mapped_column()
    askert: Mapped[float] = mapped_column()
    liike: Mapped[float] = mapped_column()
    tsto: Mapped[float] = mapped_column()
    liiken: Mapped[float] = mapped_column()
    hoito: Mapped[float] = mapped_column()
    kokoon: Mapped[float] = mapped_column()
    opetus: Mapped[float] = mapped_column()
    teoll: Mapped[float] = mapped_column()
    varast: Mapped[float] = mapped_column()
    muut: Mapped[float] = mapped_column()

class build_renovation_energy_gco2m2(Base):
    __tablename__ = "build_renovation_energy_gco2m2"
    __table_args__ = { 'schema': schema }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    erpien: Mapped[float] = mapped_column()
    rivita: Mapped[float] = mapped_column()
    askert: Mapped[float] = mapped_column()
    liike: Mapped[float] = mapped_column()
    tsto: Mapped[float] = mapped_column()
    liiken: Mapped[float] = mapped_column()
    hoito: Mapped[float] = mapped_column()
    kokoon: Mapped[float] = mapped_column()
    opetus: Mapped[float] = mapped_column()
    teoll: Mapped[float] = mapped_column()
    varast: Mapped[float] = mapped_column()
    muut: Mapped[float] = mapped_column()

class cooling_proportions_kwhm2(Base):
    __tablename__ = "cooling_proportions_kwhm2"
    __table_args__ = { 'schema': schema }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    rakv: Mapped[int] = mapped_column(primary_key=True)
    rakennus_tyyppi: Mapped[str] = mapped_column(primary_key=True)
    jaahdytys_osuus: Mapped[float] = mapped_column()
    jaahdytys_kwhm2: Mapped[float] = mapped_column()
    jaahdytys_kaukok: Mapped[float] = mapped_column()
    jaahdytys_sahko: Mapped[float] = mapped_column()
    jaahdytys_pumput: Mapped[float] = mapped_column()
    jaahdytys_muu: Mapped[float] = mapped_column()


class distribution_heating_systems(Base):
    __tablename__ = "distribution_heating_systems"
    __table_args__ = { 'schema': schema }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    rakv: Mapped[int] = mapped_column(primary_key=True)
    rakennus_tyyppi: Mapped[str] = mapped_column(primary_key=True)
    kaukolampo: Mapped[float] = mapped_column()
    kevyt_oljy: Mapped[float] = mapped_column()
    kaasu: Mapped[float] = mapped_column()
    sahko: Mapped[float] = mapped_column()
    puu: Mapped[float] = mapped_column()
    maalampo: Mapped[float] = mapped_column()
    muu_lammitys: Mapped[float] = mapped_column()

class electricity_home_device(Base):
    __tablename__ = "electricity_home_device"
    __table_args__ = { 'schema': schema }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    erpien: Mapped[float] = mapped_column()
    rivita: Mapped[float] = mapped_column()
    askert: Mapped[float] = mapped_column()

class electricity_home_light(Base):
    __tablename__ = "electricity_home_light"
    __table_args__ = { 'schema': schema }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    erpien: Mapped[float] = mapped_column()
    rivita: Mapped[float] = mapped_column()
    askert: Mapped[float] = mapped_column()

class electricity_iwhs_kwhm2(Base):
    __tablename__ = "electricity_iwhs_kwhm2"
    __table_args__ = { 'schema': schema }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
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
    teoll_kaivos: Mapped[float] = mapped_column()
    teoll_elint: Mapped[float] = mapped_column()
    teoll_tekst: Mapped[float] = mapped_column()
    teoll_puu: Mapped[float] = mapped_column()
    teoll_paper: Mapped[float] = mapped_column()
    teoll_kemia: Mapped[float] = mapped_column()
    teoll_miner: Mapped[float] = mapped_column()
    teoll_mjalos: Mapped[float] = mapped_column()
    teoll_metal: Mapped[float] = mapped_column()
    teoll_kone: Mapped[float] = mapped_column()
    teoll_muu: Mapped[float] = mapped_column()
    teoll_energ: Mapped[float] = mapped_column()
    teoll_vesi: Mapped[float] = mapped_column()
    teoll_yhdysk: Mapped[float] = mapped_column()
    varast: Mapped[float] = mapped_column()
    teoll: Mapped[float] = mapped_column()
    liike: Mapped[float] = mapped_column()
    myymal: Mapped[float] = mapped_column()

class electricity_property_change(Base):
    __tablename__ = "electricity_property_change"
    __table_args__ = { 'schema': schema }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    _c_9999: Mapped[float] = mapped_column("9999")
    _c_1920: Mapped[float] = mapped_column("1920")
    _c_1929: Mapped[float] = mapped_column("1929")
    _c_1939: Mapped[float] = mapped_column("1939")
    _c_1949: Mapped[float] = mapped_column("1949")
    _c_1959: Mapped[float] = mapped_column("1959")
    _c_1969: Mapped[float] = mapped_column("1969")
    _c_1979: Mapped[float] = mapped_column("1979")
    _c_1989: Mapped[float] = mapped_column("1989")
    _c_1999: Mapped[float] = mapped_column("1999")
    _c_2009: Mapped[float] = mapped_column("2009")
    _c_2010: Mapped[float] = mapped_column("2010")

class electricity_property_kwhm2(Base):
    __tablename__ = "electricity_property_kwhm2"
    __table_args__ = { 'schema': schema }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    rakv: Mapped[int] = mapped_column(primary_key=True)
    rakennus_tyyppi: Mapped[str] = mapped_column(primary_key=True)
    sahko_kiinteisto_kwhm2: Mapped[float] = mapped_column()

class iwhs_sizes(Base):
    __tablename__ = "iwhs_sizes"
    __table_args__ = { 'schema': schema }
    type: Mapped[str] = mapped_column(primary_key=True)
    several: Mapped[int] = mapped_column()
    single: Mapped[int] = mapped_column()

class occupancy(Base):
    __tablename__ = "occupancy"
    __table_args__ = { 'schema': schema }
    mun: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    erpien: Mapped[float] = mapped_column()
    rivita: Mapped[float] = mapped_column()
    askert: Mapped[float] = mapped_column()

class spaces_efficiency(Base):
    __tablename__ = "spaces_efficiency"
    __table_args__ = { 'schema': schema }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    rakv: Mapped[int] = mapped_column(primary_key=True)
    rakennus_tyyppi: Mapped[str] = mapped_column(primary_key=True)
    kaukolampo: Mapped[float] = mapped_column()
    kevyt_oljy: Mapped[float] = mapped_column()
    raskas_oljy: Mapped[float] = mapped_column()
    kaasu: Mapped[float] = mapped_column()
    sahko: Mapped[float] = mapped_column()
    puu: Mapped[float] = mapped_column()
    turve: Mapped[float] = mapped_column()
    hiili: Mapped[float] = mapped_column()
    maalampo: Mapped[float] = mapped_column()
    muu_lammitys: Mapped[float] = mapped_column()

class spaces_kwhm2(Base):
    __tablename__ = "spaces_kwhm2"
    __table_args__ = { 'schema': schema }
    mun: Mapped[str] = mapped_column(primary_key=True)
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    rakv: Mapped[int] = mapped_column(primary_key=True)
    erpien: Mapped[float] = mapped_column()
    rivita: Mapped[float] = mapped_column()
    askert: Mapped[float] = mapped_column()
    liike: Mapped[float] = mapped_column()
    tsto: Mapped[float] = mapped_column()
    liiken: Mapped[float] = mapped_column()
    hoito: Mapped[float] = mapped_column()
    kokoon: Mapped[float] = mapped_column()
    opetus: Mapped[float] = mapped_column()
    teoll: Mapped[float] = mapped_column()
    varast: Mapped[float] = mapped_column()
    muut: Mapped[float] = mapped_column()

class water_kwhm2(Base):
    __tablename__ = "water_kwhm2"
    __table_args__ = { 'schema': schema }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    rakv: Mapped[int] = mapped_column(primary_key=True)
    rakennus_tyyppi: Mapped[str] = mapped_column(primary_key=True)
    vesi_kwh_m2: Mapped[float] = mapped_column()
