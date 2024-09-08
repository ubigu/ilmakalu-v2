from app import db, create_schema

schema = 'built'
create_schema(schema)

class build_demolish_energy_gco2m2(db.Model):
    __table_args__ = { 'schema': schema }
    scenario = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    erpien = db.Column(db.Float)
    rivita = db.Column(db.Float)
    askert = db.Column(db.Float)
    liike = db.Column(db.Float)
    tsto = db.Column(db.Float)
    liiken = db.Column(db.Float)
    hoito = db.Column(db.Float)
    kokoon = db.Column(db.Float)
    opetus = db.Column(db.Float)
    teoll = db.Column(db.Float)
    varast = db.Column(db.Float)
    muut = db.Column(db.Float)

class build_materia_gco2m2(db.Model):
    __table_args__ = { 'schema': schema }
    scenario = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    erpien = db.Column(db.Float)
    rivita = db.Column(db.Float)
    askert = db.Column(db.Float)
    liike = db.Column(db.Float)
    tsto = db.Column(db.Float)
    liiken = db.Column(db.Float)
    hoito = db.Column(db.Float)
    kokoon = db.Column(db.Float)
    opetus = db.Column(db.Float)
    teoll = db.Column(db.Float)
    varast = db.Column(db.Float)
    muut = db.Column(db.Float)

class build_new_construction_energy_gco2m2(db.Model):
    __table_args__ = { 'schema': schema }
    scenario = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    erpien = db.Column(db.Float)
    rivita = db.Column(db.Float)
    askert = db.Column(db.Float)
    liike = db.Column(db.Float)
    tsto = db.Column(db.Float)
    liiken = db.Column(db.Float)
    hoito = db.Column(db.Float)
    kokoon = db.Column(db.Float)
    opetus = db.Column(db.Float)
    teoll = db.Column(db.Float)
    varast = db.Column(db.Float)
    muut = db.Column(db.Float)

class build_rebuilding_energy_gco2m2(db.Model):
    __table_args__ = { 'schema': schema }
    scenario = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    erpien = db.Column(db.Float)
    rivita = db.Column(db.Float)
    askert = db.Column(db.Float)
    liike = db.Column(db.Float)
    tsto = db.Column(db.Float)
    liiken = db.Column(db.Float)
    hoito = db.Column(db.Float)
    kokoon = db.Column(db.Float)
    opetus = db.Column(db.Float)
    teoll = db.Column(db.Float)
    varast = db.Column(db.Float)
    muut = db.Column(db.Float)

class build_rebuilding_share(db.Model):
    __table_args__ = { 'schema': schema }
    scenario = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    rakv = db.Column(db.Integer, primary_key=True)
    erpien = db.Column(db.Float)
    rivita = db.Column(db.Float)
    askert = db.Column(db.Float)
    liike = db.Column(db.Float)
    tsto = db.Column(db.Float)
    liiken = db.Column(db.Float)
    hoito = db.Column(db.Float)
    kokoon = db.Column(db.Float)
    opetus = db.Column(db.Float)
    teoll = db.Column(db.Float)
    varast = db.Column(db.Float)
    muut = db.Column(db.Float)

class build_renovation_energy_gco2m2(db.Model):
    __table_args__ = { 'schema': schema }
    scenario = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    erpien = db.Column(db.Float)
    rivita = db.Column(db.Float)
    askert = db.Column(db.Float)
    liike = db.Column(db.Float)
    tsto = db.Column(db.Float)
    liiken = db.Column(db.Float)
    hoito = db.Column(db.Float)
    kokoon = db.Column(db.Float)
    opetus = db.Column(db.Float)
    teoll = db.Column(db.Float)
    varast = db.Column(db.Float)
    muut = db.Column(db.Float)

class cooling_proportions_kwhm2(db.Model):
    __table_args__ = { 'schema': schema }
    scenario = db.Column(db.Text, primary_key=True)
    rakv = db.Column(db.Integer, primary_key=True)
    rakennus_tyyppi = db.Column(db.Text, primary_key=True)
    jaahdytys_osuus = db.Column(db.Float)
    jaahdytys_kwhm2 = db.Column(db.Float)
    jaahdytys_kaukok = db.Column(db.Float)
    jaahdytys_sahko = db.Column(db.Float)
    jaahdytys_pumput = db.Column(db.Float)
    jaahdytys_muu = db.Column(db.Float)


class distribution_heating_systems(db.Model):
    __table_args__ = { 'schema': schema }
    scenario = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    rakv = db.Column(db.Integer, primary_key=True)
    rakennus_tyyppi = db.Column(db.Text, primary_key=True)
    kaukolampo = db.Column(db.Float)
    kevyt_oljy = db.Column(db.Float)
    kaasu = db.Column(db.Float)
    sahko = db.Column(db.Float)
    puu = db.Column(db.Float)
    maalampo = db.Column(db.Float)
    muu_lammitys = db.Column(db.Float)

class electricity_home_device(db.Model):
    __table_args__ = { 'schema': schema }
    scenario = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    erpien = db.Column(db.Float)
    rivita = db.Column(db.Float)
    askert = db.Column(db.Float)

class electricity_home_light(db.Model):
    __table_args__ = { 'schema': schema }
    scenario = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    erpien = db.Column(db.Float)
    rivita = db.Column(db.Float)
    askert = db.Column(db.Float)

class electricity_iwhs_kwhm2(db.Model):
    __table_args__ = { 'schema': schema }
    scenario = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    myymal_hyper = db.Column(db.Float)
    myymal_super = db.Column(db.Float)
    myymal_pien = db.Column(db.Float)
    myymal_muu = db.Column(db.Float)
    majoit = db.Column(db.Float)
    asla = db.Column(db.Float)
    ravint = db.Column(db.Float)
    tsto = db.Column(db.Float)
    liiken = db.Column(db.Float)
    hoito = db.Column(db.Float)
    kokoon = db.Column(db.Float)
    opetus = db.Column(db.Float)
    muut = db.Column(db.Float)
    teoll_kaivos = db.Column(db.Float)
    teoll_elint = db.Column(db.Float)
    teoll_tekst = db.Column(db.Float)
    teoll_puu = db.Column(db.Float)
    teoll_paper = db.Column(db.Float)
    teoll_kemia = db.Column(db.Float)
    teoll_miner = db.Column(db.Float)
    teoll_mjalos = db.Column(db.Float)
    teoll_metal = db.Column(db.Float)
    teoll_kone = db.Column(db.Float)
    teoll_muu = db.Column(db.Float)
    teoll_energ = db.Column(db.Float)
    teoll_vesi = db.Column(db.Float)
    teoll_yhdysk = db.Column(db.Float)
    varast = db.Column(db.Float)
    teoll = db.Column(db.Float)
    liike = db.Column(db.Float)
    myymal = db.Column(db.Float)

class electricity_property_change(db.Model):
    __table_args__ = { 'schema': schema }
    scenario = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    _c_9999 = db.Column("9999",db.Float)
    _c_1920 = db.Column("1920",db.Float)
    _c_1929 = db.Column("1929",db.Float)
    _c_1939 = db.Column("1939",db.Float)
    _c_1949 = db.Column("1949",db.Float)
    _c_1959 = db.Column("1959",db.Float)
    _c_1969 = db.Column("1969",db.Float)
    _c_1979 = db.Column("1979",db.Float)
    _c_1989 = db.Column("1989",db.Float)
    _c_1999 = db.Column("1999",db.Float)
    _c_2009 = db.Column("2009",db.Float)
    _c_2010 = db.Column("2010",db.Float)

class electricity_property_kwhm2(db.Model):
    __table_args__ = { 'schema': schema }
    scenario = db.Column(db.Text, primary_key=True)
    rakv = db.Column(db.Integer, primary_key=True)
    rakennus_tyyppi = db.Column(db.Text, primary_key=True)
    sahko_kiinteisto_kwhm2 = db.Column(db.Float)

class iwhs_sizes(db.Model):
    __table_args__ = { 'schema': schema }
    type = db.Column(db.Text, primary_key=True)
    several = db.Column(db.Integer)
    single = db.Column(db.Integer)

class occupancy(db.Model):
    __table_args__ = { 'schema': schema }
    mun = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    erpien = db.Column(db.Float)
    rivita = db.Column(db.Float)
    askert = db.Column(db.Float)

class spaces_efficiency(db.Model):
    __table_args__ = { 'schema': schema }
    scenario = db.Column(db.Text, primary_key=True)
    rakv = db.Column(db.Integer, primary_key=True)
    rakennus_tyyppi = db.Column(db.Text, primary_key=True)
    kaukolampo = db.Column(db.Float)
    kevyt_oljy = db.Column(db.Float)
    raskas_oljy = db.Column(db.Float)
    kaasu = db.Column(db.Float)
    sahko = db.Column(db.Float)
    puu = db.Column(db.Float)
    turve = db.Column(db.Float)
    hiili = db.Column(db.Float)
    maalampo = db.Column(db.Float)
    muu_lammitys = db.Column(db.Float)

class spaces_kwhm2(db.Model):
    __table_args__ = { 'schema': schema }
    mun = db.Column(db.Text, primary_key=True)
    scenario = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    rakv = db.Column(db.Integer, primary_key=True)
    erpien = db.Column(db.Float)
    rivita = db.Column(db.Float)
    askert = db.Column(db.Float)
    liike = db.Column(db.Float)
    tsto = db.Column(db.Float)
    liiken = db.Column(db.Float)
    hoito = db.Column(db.Float)
    kokoon = db.Column(db.Float)
    opetus = db.Column(db.Float)
    teoll = db.Column(db.Float)
    varast = db.Column(db.Float)
    muut = db.Column(db.Float)

class water_kwhm2(db.Model):
    __table_args__ = { 'schema': schema }
    scenario = db.Column(db.Text, primary_key=True)
    rakv = db.Column(db.Integer, primary_key=True)
    rakennus_tyyppi = db.Column(db.Text, primary_key=True)
    vesi_kwh_m2 = db.Column(db.Float)