from fastapi import FastAPI
from models import built, delineations, energy, grid_globals, traffic
from database import engine, Base
from sqlalchemy import event
from csv import DictReader
app = FastAPI()

@event.listens_for(Base.metadata, 'after_create', once=True)
def import_data_from_csv(target, connection, **kw):
    """ This function assumes that the path follows
    the structure '{root_dir}/{schema}/{table_name}.csv' """
    for table in target.tables.values():
        try:
            file_path = f'database/{table.schema}/{table.name}.csv'
            with open(file_path, encoding='utf-8-sig') as f:
                connection.execute(
                    table.insert(),
                    [{k: v for k, v in row.items()}
                    for row in DictReader(f, skipinitialspace=True, delimiter=";")]
                )
        except Exception as error:
            print(error)
            continue

Base.metadata.create_all(engine)

@app.get("/")
def read_root():
    return {"Hello": "World"}