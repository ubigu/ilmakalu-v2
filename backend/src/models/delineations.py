from database import Base, create_schema
from sqlalchemy.orm import Mapped, mapped_column

schema = 'delineations'
create_schema(schema)

class centroids(Base):
    __tablename__ = "centroids"
    __table_args__ = { 'schema': schema }
    WKT: Mapped[str] = mapped_column()
    id: Mapped[int] = mapped_column(primary_key=True)
    keskustyyp: Mapped[str] = mapped_column()
    keskusnimi: Mapped[str] = mapped_column()

class grid(Base):
    __tablename__ = "grid"
    __table_args__ = { 'schema': schema }
    WKT: Mapped[str] = mapped_column()
    xyind: Mapped[str] = mapped_column(primary_key=True)
    mun: Mapped[int] = mapped_column()
    zone: Mapped[str] = mapped_column()
    centdist: Mapped[int] = mapped_column()