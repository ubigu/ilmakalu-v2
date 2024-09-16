from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema
from sqlalchemy.ext.declarative import declarative_base
from csv import DictReader
import os

# Replace with your own PostgreSQL instance
DATABASE_URL = 'postgresql://docker:docker@ilmakalu_user:5432/ilmakalu_data'

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

Base = declarative_base()

def create_schema(schema):
    with Session() as session:
        session.execute(CreateSchema(schema, if_not_exists=True))
        session.commit()

def import_data_from_csv(connection, file, table):
    with open(file, encoding='utf-8-sig') as f:
        records = [
            {k: v for k, v in row.items()}
            for row in DictReader(f, skipinitialspace=True, delimiter=";")
        ]
        for record in records:
            try:
                with connection.begin_nested():
                    connection.execute(table.insert().values(record))
            except Exception:
                continue

def initialize_database(target, connection, **kw):
    """ It is assumed that the path follows
    the structure '{root_dir}/{schema}/{table_name}.csv' """
    root_dir = 'database'
    tables = target.tables
    table_keys = tables.keys()
    schemas = next(os.walk(root_dir))[1]

    for schema in schemas:
        dir = os.path.join(root_dir, schema)
        for filename in os.listdir(dir):
            table_name, ext = os.path.splitext(os.fsdecode(filename))
            table = f'{schema}.{table_name}'
            if not (table in table_keys and ext == ".csv"): 
                continue
            print(f'Importing data into table {table}...')
            import_data_from_csv(connection, os.path.join(dir, filename), tables[table])

event.listen(Base.metadata, 'after_create', initialize_database, once=True)