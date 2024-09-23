from sqlmodel import SQLModel, Field

schema = 'delineations'

class centroids(SQLModel, table=True):
    __table_args__ = { "schema": schema }
    WKT: str
    id: int = Field(primary_key=True)
    keskustyyp: str
    keskusnimi: str

class grid(SQLModel, table=True):
    __table_args__ = { "schema": schema }
    WKT: str
    xyind: str = Field(primary_key=True)
    mun: int
    zone: str
    centdist: int