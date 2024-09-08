from flask import Flask, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS  
import os
import csv
from sqlalchemy.schema import CreateSchema

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

def create_schema(schema):
  with db.engine.connect() as conn:
    if not conn.dialect.has_schema(conn, schema):
      conn.execute(CreateSchema(schema))

def _import_data_from_csv():
  """ This function assumes that the path follows
  the structure '{root_dir}/{schema}/{table_name}.csv' """
  root_dir = 'database'
  globals_dict = globals()
  tables = db.Model.metadata.tables.values()

  for table in tables:
    schema = table.schema
    table_name = table.name
    try:
      model = globals_dict[table_name]
      file_path = f'{root_dir}/{schema}/{table_name}.csv'

      with open(file_path) as f:
        reader = csv.reader(f, delimiter=';')
        header = next(reader)

        for i in reader:
          try:
            kwargs = {}
            for column, value in zip(header,i):
              column = column.replace('\ufeff', '')
              if column[0].isdigit():
                column = '_c_'+column
              kwargs[column] = value
            try:
              db.session.merge(model(**kwargs))
              db.session.commit()
            except:
              db.session.rollback()
          except:
            continue
    except:
      continue

from models.db_built import *
from models.db_delineations import *
from models.db_energy import *
from models.db_grid_globals import *
from models.db_traffic import *

db.create_all()
_import_data_from_csv()

#create a test route
@app.route('/test', methods=['GET'])
def test():
  return make_response(jsonify({'message': 'test route'}), 200)