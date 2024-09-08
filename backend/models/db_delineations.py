from app import db, create_schema

schema = 'delineations'
create_schema(schema)

class centroids(db.Model):
    __table_args__ = { 'schema': schema }
    WKT = db.Column(db.Text)
    id = db.Column(db.Integer, primary_key=True)
    keskustyyp = db.Column(db.Text)
    keskusnimi = db.Column(db.Text)

class grid(db.Model):
    __table_args__ = { 'schema': schema }
    WKT = db.Column(db.Text)
    xyind = db.Column(db.BigInteger, primary_key=True)
    mun = db.Column(db.Integer)
    zone = db.Column(db.BigInteger)
    centdist = db.Column(db.Integer)