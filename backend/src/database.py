from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Replace with your own PostgreSQL instance
DATABASE_URL = 'postgresql://docker:docker@ilmakalu_user:5432/ilmakalu_data'

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

Base = declarative_base()