from .database import create_schema
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

create_schema("built")

class build_demolish_energy_gco2m2(Base):
    __tablename__ = "build_demolish_energy_gco2m2"
    __table_args__ = { "schema": "built" }
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
    __table_args__ = { 'schema': "built" }
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
    __table_args__ = { 'schema': "built" }
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
    __table_args__ = { 'schema': "built" }
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
    __table_args__ = { 'schema': "built" }
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
    __table_args__ = { 'schema': "built" }
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
    __table_args__ = { 'schema': "built" }
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
    __table_args__ = { 'schema': "built" }
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
    __table_args__ = { 'schema': "built" }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    erpien: Mapped[float] = mapped_column()
    rivita: Mapped[float] = mapped_column()
    askert: Mapped[float] = mapped_column()

class electricity_home_light(Base):
    __tablename__ = "electricity_home_light"
    __table_args__ = { 'schema': "built" }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    erpien: Mapped[float] = mapped_column()
    rivita: Mapped[float] = mapped_column()
    askert: Mapped[float] = mapped_column()

class electricity_iwhs_kwhm2(Base):
    __tablename__ = "electricity_iwhs_kwhm2"
    __table_args__ = { 'schema': "built" }
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
    __table_args__ = { 'schema': "built" }
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
    __table_args__ = { 'schema': "built" }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    rakv: Mapped[int] = mapped_column(primary_key=True)
    rakennus_tyyppi: Mapped[str] = mapped_column(primary_key=True)
    sahko_kiinteisto_kwhm2: Mapped[float] = mapped_column()

class iwhs_sizes(Base):
    __tablename__ = "iwhs_sizes"
    __table_args__ = { 'schema': "built" }
    type: Mapped[str] = mapped_column(primary_key=True)
    several: Mapped[int] = mapped_column()
    single: Mapped[int] = mapped_column()

class occupancy(Base):
    __tablename__ = "occupancy"
    __table_args__ = { 'schema': "built" }
    mun: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    erpien: Mapped[float] = mapped_column()
    rivita: Mapped[float] = mapped_column()
    askert: Mapped[float] = mapped_column()

class spaces_efficiency(Base):
    __tablename__ = "spaces_efficiency"
    __table_args__ = { 'schema': "built" }
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
    __table_args__ = { 'schema': "built" }
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
    __table_args__ = { 'schema': "built" }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    rakv: Mapped[int] = mapped_column(primary_key=True)
    rakennus_tyyppi: Mapped[str] = mapped_column(primary_key=True)
    vesi_kwh_m2: Mapped[float] = mapped_column()

create_schema("delineations")

class centroids(Base):
    __tablename__ = "centroids"
    __table_args__ = { 'schema': "delineations" }
    WKT: Mapped[str] = mapped_column()
    id: Mapped[int] = mapped_column(primary_key=True)
    keskustyyp: Mapped[str] = mapped_column()
    keskusnimi: Mapped[str] = mapped_column()

class grid(Base):
    __tablename__ = "grid"
    __table_args__ = { 'schema': "delineations" }
    WKT: Mapped[str] = mapped_column()
    xyind: Mapped[int] = mapped_column(primary_key=True)
    mun: Mapped[int] = mapped_column()
    zone: Mapped[int] = mapped_column()
    centdist: Mapped[int] = mapped_column()

create_schema("energy")

class cooling_gco2kwh(Base):
    __tablename__ = "cooling_gco2kwh"
    __table_args__ = { 'schema': "energy" }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    kaukok: Mapped[int] = mapped_column()
    sahko: Mapped[int] = mapped_column()
    pumput: Mapped[int] = mapped_column()
    muu: Mapped[int] = mapped_column()

class district_heating(Base):
    __tablename__ = "district_heating"
    __table_args__ = { 'schema': "energy" }
    mun: Mapped[str] = mapped_column(primary_key=True)
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    em: Mapped[int] = mapped_column()
    hjm: Mapped[int] = mapped_column()

class electricity(Base):
    __tablename__ = "electricity"
    __table_args__ = { 'schema': "energy" }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    metodi: Mapped[str] = mapped_column(primary_key=True)
    paastolaji: Mapped[str] = mapped_column(primary_key=True)
    gco2kwh: Mapped[int] = mapped_column()

class electricity_home_percapita(Base):
    __tablename__ = "electricity_home_percapita"
    __table_args__ = { 'schema': "energy" }
    mun: Mapped[str] = mapped_column(primary_key=True)
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    sahko_koti_as: Mapped[int] = mapped_column()

class heat_source_change(Base):
    __tablename__ = "heat_source_change"
    __table_args__ = { 'schema': "energy" }
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
    __table_args__ = { 'schema': "energy" }
    mun: Mapped[str] = mapped_column(primary_key=True)
    mun_name: Mapped[str] = mapped_column()
    degreedays: Mapped[int] = mapped_column()
    multiplier: Mapped[float] = mapped_column()

class spaces_gco2kwh(Base):
    __tablename__ = "spaces_gco2kwh"
    __table_args__ = { 'schema': "energy" }
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

create_schema("grid_globals")

class buildings(Base):
    __tablename__ = "buildings"
    __table_args__ = { 'schema': "grid_globals" }
    xyind: Mapped[int] = mapped_column(primary_key=True)
    rakv: Mapped[int] = mapped_column(primary_key=True)
    energiam: Mapped[str] = mapped_column(primary_key=True)
    rakyht_lkm: Mapped[int] = mapped_column()
    teoll_lkm: Mapped[int] = mapped_column()
    varast_lkm: Mapped[int] = mapped_column()
    rakyht_ala: Mapped[int] = mapped_column()
    asuin_ala: Mapped[int] = mapped_column()
    erpien_ala: Mapped[int] = mapped_column()
    rivita_ala: Mapped[int] = mapped_column()
    askert_ala: Mapped[int] = mapped_column()
    liike_ala: Mapped[int] = mapped_column()
    myymal_ala: Mapped[int] = mapped_column()
    myymal_pien_ala: Mapped[int] = mapped_column()
    myymal_super_ala: Mapped[int] = mapped_column()
    myymal_hyper_ala: Mapped[int] = mapped_column()
    myymal_muu_ala: Mapped[int] = mapped_column()
    majoit_ala: Mapped[int] = mapped_column()
    asla_ala: Mapped[int] = mapped_column()
    ravint_ala: Mapped[int] = mapped_column()
    tsto_ala: Mapped[int] = mapped_column()
    liiken_ala: Mapped[int] = mapped_column()
    hoito_ala: Mapped[int] = mapped_column()
    kokoon_ala: Mapped[int] = mapped_column()
    opetus_ala: Mapped[int] = mapped_column()
    teoll_ala: Mapped[int] = mapped_column()
    teoll_elint_ala: Mapped[int] = mapped_column()
    teoll_tekst_ala: Mapped[int] = mapped_column()
    teoll_puu_ala: Mapped[int] = mapped_column()
    teoll_paper_ala: Mapped[int] = mapped_column()
    teoll_miner_ala: Mapped[int] = mapped_column()
    teoll_kemia_ala: Mapped[int] = mapped_column()
    teoll_kone_ala: Mapped[int] = mapped_column()
    teoll_mjalos_ala: Mapped[int] = mapped_column()
    teoll_metal_ala: Mapped[int] = mapped_column()
    teoll_vesi_ala: Mapped[int] = mapped_column()
    teoll_energ_ala: Mapped[int] = mapped_column()
    teoll_yhdysk_ala: Mapped[int] = mapped_column()
    teoll_kaivos_ala: Mapped[int] = mapped_column()
    teoll_muu_ala: Mapped[int] = mapped_column()
    varast_ala: Mapped[int] = mapped_column()
    muut_ala: Mapped[int] = mapped_column()

class clc(Base):
    __tablename__ = "clc"
    __table_args__ = { 'schema': "grid_globals" }
    vuosi: Mapped[int] = mapped_column()
    kunta: Mapped[str] = mapped_column()
    maa_ha: Mapped[float] = mapped_column()
    vesi_ha: Mapped[float] = mapped_column()
    clc1111: Mapped[float] = mapped_column()
    clc1121: Mapped[float] = mapped_column()
    clc1211: Mapped[float] = mapped_column()
    clc1212: Mapped[float] = mapped_column()
    clc1221: Mapped[float] = mapped_column()
    clc1231: Mapped[float] = mapped_column()
    clc1241: Mapped[float] = mapped_column()
    clc1311: Mapped[float] = mapped_column()
    clc1312: Mapped[float] = mapped_column()
    clc1321: Mapped[float] = mapped_column()
    clc1331: Mapped[float] = mapped_column()
    clc1411: Mapped[float] = mapped_column()
    clc1421: Mapped[float] = mapped_column()
    clc1422: Mapped[float] = mapped_column()
    clc1423: Mapped[float] = mapped_column()
    clc1424: Mapped[float] = mapped_column()
    clc2111: Mapped[float] = mapped_column()
    clc2221: Mapped[float] = mapped_column()
    clc2311: Mapped[float] = mapped_column()
    clc2312: Mapped[float] = mapped_column()
    clc2431: Mapped[float] = mapped_column()
    clc2441: Mapped[float] = mapped_column()
    clc3111: Mapped[float] = mapped_column()
    clc3112: Mapped[float] = mapped_column()
    clc3121: Mapped[float] = mapped_column()
    clc3122: Mapped[float] = mapped_column()
    clc3123: Mapped[float] = mapped_column()
    clc3131: Mapped[float] = mapped_column()
    clc3132: Mapped[float] = mapped_column()
    clc3133: Mapped[float] = mapped_column()
    clc3211: Mapped[float] = mapped_column()
    clc3221: Mapped[float] = mapped_column()
    clc3241: Mapped[float] = mapped_column()
    clc3242: Mapped[float] = mapped_column()
    clc3243: Mapped[float] = mapped_column()
    clc3244: Mapped[float] = mapped_column()
    clc3246: Mapped[float] = mapped_column()
    clc3311: Mapped[float] = mapped_column()
    clc3321: Mapped[float] = mapped_column()
    clc3331: Mapped[float] = mapped_column()
    clc4111: Mapped[float] = mapped_column()
    clc4112: Mapped[float] = mapped_column()
    clc4121: Mapped[float] = mapped_column()
    clc4122: Mapped[float] = mapped_column()
    clc4211: Mapped[float] = mapped_column()
    clc4212: Mapped[float] = mapped_column()
    clc5111: Mapped[float] = mapped_column()
    clc5121: Mapped[float] = mapped_column()
    clc5231: Mapped[float] = mapped_column()
    xyind: Mapped[int] = mapped_column(primary_key=True)

class employ(Base):
    __tablename__ = "employ"
    __table_args__ = { 'schema': "grid_globals" }
    vuosi: Mapped[int] = mapped_column(primary_key=True)
    kunta: Mapped[str] = mapped_column()
    tp_yht: Mapped[int] = mapped_column()
    xyind: Mapped[int] = mapped_column(primary_key=True)

class pop(Base):
    __tablename__ = "pop"
    __table_args__ = { 'schema': "grid_globals" }
    vuosi: Mapped[int] = mapped_column(primary_key=True)
    kunta: Mapped[str] = mapped_column()
    xyind: Mapped[int] = mapped_column(primary_key=True)
    v_yht: Mapped[int] = mapped_column()
    v_0_6: Mapped[int] = mapped_column()
    v_7_14: Mapped[int] = mapped_column()
    v_15_17: Mapped[int] = mapped_column()
    v_18_29: Mapped[int] = mapped_column()
    v_30_49: Mapped[int] = mapped_column()
    v_50_64: Mapped[int] = mapped_column()
    v_65_74: Mapped[int] = mapped_column()
    v_75: Mapped[int] = mapped_column()

create_schema("traffic")

class citizen_traffic_stress(Base):
    __tablename__ = "citizen_traffic_stress"
    __table_args__ = { 'schema': "traffic" }
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
    __table_args__ = { 'schema': "traffic" }
    zone: Mapped[int] = mapped_column(primary_key=True)
    jalkapyora: Mapped[float] = mapped_column()
    bussi: Mapped[float] = mapped_column()
    raide: Mapped[float] = mapped_column()
    hlauto: Mapped[float] = mapped_column()
    muu: Mapped[float] = mapped_column()

class hlt_kmchange(Base):
    __tablename__ = "hlt_kmchange"
    __table_args__ = { 'schema': "traffic" }
    zone: Mapped[int] = mapped_column(primary_key=True)
    jalkapyora: Mapped[float] = mapped_column()
    bussi: Mapped[float] = mapped_column()
    raide: Mapped[float] = mapped_column()
    hlauto: Mapped[float] = mapped_column()
    muu: Mapped[float] = mapped_column()

class hlt_lookup(Base):
    __tablename__ = "hlt_lookup"
    __table_args__ = { 'schema': "traffic" }
    mun: Mapped[str] = mapped_column(primary_key=True)
    hlt_table: Mapped[str] = mapped_column()

class hlt_workshare(Base):
    __tablename__ = "hlt_workshare"
    __table_args__ = { 'schema': "traffic" }
    zone: Mapped[int] = mapped_column(primary_key=True)
    jalkapyora: Mapped[float] = mapped_column()
    bussi: Mapped[float] = mapped_column()
    raide: Mapped[float] = mapped_column()
    hlauto: Mapped[float] = mapped_column()
    muu: Mapped[float] = mapped_column()

class industr_performance(Base):
    __tablename__ = "industr_performance"
    __table_args__ = { 'schema': "traffic" }
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
    __table_args__ = { 'schema': "traffic" }
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
    __table_args__ = { 'schema': "traffic" }
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
    __table_args__ = { 'schema': "traffic" }
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    share: Mapped[float] = mapped_column()

class power_kwhkm(Base):
    __tablename__ = "power_kwhkm"
    __table_args__ = { 'schema': "traffic" }
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
    __table_args__ = { 'schema': "traffic" }
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
    __table_args__ = { 'schema': "traffic" }
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
    __table_args__ = { 'schema': "traffic" }
    mun: Mapped[str] = mapped_column(primary_key=True)
    scenario: Mapped[str] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    jalkapyora: Mapped[float] = mapped_column()
    bussi: Mapped[float] = mapped_column()
    raide: Mapped[float] = mapped_column()
    hlauto: Mapped[float] = mapped_column()
    muu: Mapped[float] = mapped_column()

create_schema("functions")
