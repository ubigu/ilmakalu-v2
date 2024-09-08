from app import db, create_schema

schema = 'traffic'
create_schema(schema)

class citizen_traffic_stress(db.Model):
    __table_args__ = { 'schema': schema }
    mun = db.Column(db.Text, primary_key=True)
    scenario = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    jalkapyora = db.Column(db.Float)
    bussi = db.Column(db.Float)
    raide = db.Column(db.Float)
    hlauto = db.Column(db.Float)
    muu = db.Column(db.Float)

class hlt_2015_tre(db.Model):
    __table_args__ = { 'schema': schema }
    zone = db.Column(db.Integer, primary_key=True)
    jalkapyora = db.Column(db.Float)
    bussi = db.Column(db.Float)
    raide = db.Column(db.Float)
    hlauto = db.Column(db.Float)
    muu = db.Column(db.Float)

class hlt_kmchange(db.Model):
    __table_args__ = { 'schema': schema }
    zone = db.Column(db.Integer, primary_key=True)
    jalkapyora = db.Column(db.Float)
    bussi = db.Column(db.Float)
    raide = db.Column(db.Float)
    hlauto = db.Column(db.Float)
    muu = db.Column(db.Float)

class hlt_lookup(db.Model):
    __table_args__ = { 'schema': schema }
    mun = db.Column(db.Text, primary_key=True)
    hlt_table = db.Column(db.Text)

class hlt_workshare(db.Model):
    __table_args__ = { 'schema': schema }
    zone = db.Column(db.Integer, primary_key=True)
    jalkapyora = db.Column(db.Float)
    bussi = db.Column(db.Float)
    raide = db.Column(db.Float)
    hlauto = db.Column(db.Float)
    muu = db.Column(db.Float)

class industr_performance(db.Model):
    __table_args__ = { 'schema': schema }
    scenario = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    kmuoto = db.Column(db.Text, primary_key=True)
    teoll_kaivos = db.Column(db.Integer)
    teoll_elint = db.Column(db.Integer)
    teoll_tekst = db.Column(db.Integer)
    teoll_puu = db.Column(db.Integer)
    teoll_paper = db.Column(db.Integer)
    teoll_kemia = db.Column(db.Integer)
    teoll_miner = db.Column(db.Integer)
    teoll_mjalos = db.Column(db.Integer)
    teoll_metal = db.Column(db.Integer)
    teoll_kone = db.Column(db.Integer)
    teoll_muu = db.Column(db.Integer)
    teoll_energ = db.Column(db.Integer)
    teoll_vesi = db.Column(db.Integer)
    teoll_yhdysk = db.Column(db.Integer)
    varast = db.Column(db.Integer)
    teoll = db.Column(db.Integer)

class industr_transport_km(db.Model):
    __table_args__ = { 'schema': schema }
    scenario = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    kmuoto = db.Column(db.Text, primary_key=True)
    teoll_kaivos = db.Column(db.Integer)
    teoll_elint = db.Column(db.Integer)
    teoll_tekst = db.Column(db.Integer)
    teoll_puu = db.Column(db.Integer)
    teoll_paper = db.Column(db.Integer)
    teoll_kemia = db.Column(db.Integer)
    teoll_miner = db.Column(db.Integer)
    teoll_mjalos = db.Column(db.Integer)
    teoll_metal = db.Column(db.Integer)
    teoll_kone = db.Column(db.Integer)
    teoll_muu = db.Column(db.Integer)
    teoll_energ = db.Column(db.Integer)
    teoll_vesi = db.Column(db.Integer)
    teoll_yhdysk = db.Column(db.Integer)
    varast = db.Column(db.Integer)
    teoll = db.Column(db.Integer)

class mode_power_distribution(db.Model):
    __table_args__ = { 'schema': schema }
    mun = db.Column(db.Text, primary_key=True)
    scenario = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    kmuoto = db.Column(db.Text, primary_key=True)
    kvoima_bensiini = db.Column(db.Float)
    kvoima_etanoli = db.Column(db.Float)
    kvoima_diesel = db.Column(db.Float)
    kvoima_kaasu = db.Column(db.Float)
    kvoima_phev_b = db.Column(db.Float)
    kvoima_phev_d = db.Column(db.Float)
    kvoima_ev = db.Column(db.Float)
    kvoima_vety = db.Column(db.Float)
    kvoima_muut = db.Column(db.Float)

class power_fossil_share(db.Model):
    __table_args__ = { 'schema': schema }
    scenario = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    share = db.Column(db.Float)

class power_kwhkm(db.Model):
    __table_args__ = { 'schema': schema }
    scenario = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    kmuoto = db.Column(db.Text, primary_key=True)
    kvoima_bensiini = db.Column(db.Float)
    kvoima_etanoli = db.Column(db.Float)
    kvoima_diesel = db.Column(db.Float)
    kvoima_kaasu = db.Column(db.Float)
    kvoima_phev_b = db.Column(db.Float)
    kvoima_phev_d = db.Column(db.Float)
    kvoima_ev = db.Column(db.Float)
    kvoima_vety = db.Column(db.Float)
    kvoima_muut = db.Column(db.Float)

class service_performance(db.Model):
    __table_args__ = { 'schema': schema }
    scenario = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    kmuoto = db.Column(db.Text, primary_key=True)
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

class services_transport_km(db.Model):
    __table_args__ = { 'schema': schema }
    scenario = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    kmuoto = db.Column(db.Text, primary_key=True)
    myymal_hyper = db.Column(db.Integer)
    myymal_super = db.Column(db.Integer)
    myymal_pien = db.Column(db.Integer)
    myymal_muu = db.Column(db.Integer)
    majoit = db.Column(db.Integer)
    asla = db.Column(db.Integer)
    ravint = db.Column(db.Integer)
    tsto = db.Column(db.Integer)
    liiken = db.Column(db.Integer)
    hoito = db.Column(db.Integer)
    kokoon = db.Column(db.Integer)
    opetus = db.Column(db.Integer)
    muut = db.Column(db.Integer)

class workers_traffic_stress(db.Model):
    __table_args__ = { 'schema': schema }
    mun = db.Column(db.Text, primary_key=True)
    scenario = db.Column(db.Text, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    jalkapyora = db.Column(db.Float)
    bussi = db.Column(db.Float)
    raide = db.Column(db.Float)
    hlauto = db.Column(db.Float)
    muu = db.Column(db.Float)
