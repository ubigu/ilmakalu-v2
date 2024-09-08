from app import db, createSchema

schema = 'delineations'
createSchema(schema)

class centroids(db.Model):
    __table_args__ = { 'schema': schema }
    WKT = db.Column(db.Text)
    id = db.Column(db.Integer, primary_key=True)
    keskustyyp = db.Column(db.Text)
    keskusnimi = db.Column(db.Text)

class grid(db.Model):
    __table_args__ = { 'schema': schema }
    WKT = db.Column(db.Text)
    xyind = db.Column(db.Integer, primary_key=True)
    mun = db.Column(db.Integer)
    zone = db.Column(db.Integer)
    centdist = db.Column(db.Integer)