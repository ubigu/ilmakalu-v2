from app import db, createSchema

schema = 'energy'
createSchema(schema)

class cooling_gco2kwh(db.Model):
    __table_args__ = { 'schema': schema }
    scenario = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    kaukok = db.Column(db.Integer)
    sahko = db.Column(db.Integer)
    pumput = db.Column(db.Integer)
    muu = db.Column(db.Integer)

class district_heating(db.Model):
    __table_args__ = { 'schema': schema }
    mun = db.Column(db.Text, primary_key=True)
    scenario = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    em = db.Column(db.Integer)
    hjm = db.Column(db.Integer)

class electricity(db.Model):
    __table_args__ = { 'schema': schema }
    scenario = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    metodi = db.Column(db.Text, primary_key=True)
    paastolaji = db.Column(db.Text, primary_key=True)
    gco2kwh = db.Column(db.Integer)

class electricity_home_percapita(db.Model):
    __table_args__ = { 'schema': schema }
    mun = db.Column(db.Text, primary_key=True)
    scenario = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    sahko_koti_as = db.Column(db.Integer)

class heat_source_change(db.Model):
    __table_args__ = { 'schema': schema }
    scenario = db.Column(db.Text, primary_key=True)
    rakennus_tyyppi = db.Column(db.Text, primary_key=True)
    lammitysmuoto = db.Column(db.Text, primary_key=True)
    kaukolampo = db.Column(db.Float)
    kevyt_oljy = db.Column(db.Float)
    kaasu = db.Column(db.Float)
    sahko = db.Column(db.Float)
    puu = db.Column(db.Float)
    maalampo = db.Column(db.Float)

class heating_degree_days(db.Model):
    __table_args__ = { 'schema': schema }
    mun = db.Column(db.Text, primary_key=True)
    mun_name = db.Column(db.Text)
    degreedays = db.Column(db.Integer)
    multiplier = db.Column(db.Float)

class spaces_gco2kwh(db.Model):
    __table_args__ = { 'schema': schema }
    vuosi = db.Column(db.Integer, primary_key=True)
    kaukolampo = db.Column(db.Integer)
    kevyt_oljy = db.Column(db.Integer)
    raskas_oljy = db.Column(db.Integer)
    kaasu = db.Column(db.Integer)
    sahko = db.Column(db.Integer)
    puu = db.Column(db.Integer)
    turve = db.Column(db.Integer)
    hiili = db.Column(db.Integer)
    maalampo = db.Column(db.Integer)
    muu_lammitys = db.Column(db.Integer)