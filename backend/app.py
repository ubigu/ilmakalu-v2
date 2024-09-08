from flask import Flask, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS  
from os import environ
import csv
from sqlalchemy.schema import CreateSchema

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

app.config['SQLALCHEMY_DATABASE_URI'] = environ.get('DATABASE_URL')
db = SQLAlchemy(app)

def createSchema(schema):
  with db.engine.connect() as conn:
      if not conn.dialect.has_schema(conn, schema):
          conn.execute(CreateSchema(schema))

from models.db_built import *
from models.db_delineations import *
from models.db_energy import *
from models.db_grid_globals import *
from models.db_traffic import *

db.create_all()

"""To do
entries = []
with open("database/built/build_demolish_energy_gco2m2.csv") as f:
  reader = csv.reader(f, delimiter=';')
  header = next(reader)
  for i in reader:
    kwargs = {column.replace('\ufeff', ''): value for column, value in zip(header, i)}
    entries.append(build_demolish_energy_gco2m2(**kwargs))
  db.session.add_all(entries)
  db.session.commit()"""

#create a test route
@app.route('/test', methods=['GET'])
def test():
  return make_response(jsonify({'message': 'test route'}), 200)