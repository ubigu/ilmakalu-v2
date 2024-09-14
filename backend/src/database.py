from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema

# Replace with your own PostgreSQL instance
DATABASE_URL = 'postgresql://docker:docker@ilmakalu_user:5432/ilmakalu_data'

engine = create_engine(DATABASE_URL)

def create_schema(schema):
    with engine.connect() as connection:
        connection.execute(CreateSchema(schema, if_not_exists=True))
        connection.commit()

SessionLocal = sessionmaker(bind=engine)