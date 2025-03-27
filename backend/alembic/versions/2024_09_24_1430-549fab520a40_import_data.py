"""Import data

Revision ID: 549fab520a40
Revises: fad8f477458f
Create Date: 2024-09-24 14:30:03.831130

"""

import os
from csv import DictReader
from typing import Sequence, Union

import geopandas as gpd
import requests
import sqlalchemy as sa
import sqlmodel
from fiona.io import ZipMemoryFile

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "549fab520a40"
down_revision: Union[str, None] = "fad8f477458f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

tables = sqlmodel.SQLModel.metadata.tables
delimiter = ";"
encoding = "utf-8-sig"
geom_col = "geom"


def __import_from_sql(conn, file):
    try:
        with open(file) as f:
            stmt = sa.sql.text(f.read())
            with conn.begin_nested():
                conn.execute(stmt)
    except Exception:
        return


def __import_from_csv(conn, file, name, schema):
    """It is assumed that the file path follows
    the pattern '{root_dir}/{schema}/{table_name}.csv'"""
    table_name = f"{schema}.{name}"
    try:
        with open(file, encoding=encoding) as f:
            with conn.begin_nested():
                stmt = f"COPY {table_name} FROM STDIN DELIMITER '{delimiter}' CSV HEADER;"
                conn.connection.cursor().copy_expert(stmt, f)
    except Exception:
        # If COPY fails, try to insert rows one by one (this is slow)
        if table_name not in tables:
            return
        table = tables[table_name]
        with open(file, encoding=encoding) as f:
            for row in DictReader(f, skipinitialspace=True, delimiter=delimiter):
                try:
                    with conn.begin_nested():
                        conn.execute(table.insert().values({k: v for k, v in row.items()}))
                except Exception:
                    continue


def __import_centroids(conn):
    __update_delineations_srid("centroids")

    r = requests.get("https://wwwd3.ymparisto.fi/d3/gis_data/spesific/KeskustaAlueet2021.zip")
    if not r.ok:
        raise OSError("Failed to fetch the centroid data from the API")

    with ZipMemoryFile(r.content) as memfile:
        with memfile.open() as src:
            gdf = gpd.GeoDataFrame.from_features(src, crs=src.crs).rename_geometry(geom_col)
            gdf[geom_col] = gdf[geom_col].centroid
            gdf["id"] = gdf.index + 1
            gdf = gdf[[geom_col, "id", "Keskustyyp", "KeskusNimi"]]
            gdf.columns = [c.lower() for c in gdf.columns]
            gdf.to_postgis("centroids", con=conn, if_exists="append", schema="delineations")


def __update_delineations_srid(tbl):
    op.execute(f"SELECT UpdateGeometrySRID('delineations','{tbl}','{geom_col}',3067)")


def upgrade() -> None:
    conn = op.get_bind()
    __import_centroids(conn)

    for subdir, _, files in os.walk("database"):
        for file_name in files:
            file = os.path.join(subdir, file_name)
            print(f"Importing from file {file}...")
            name, ext = os.path.splitext(os.fsdecode(file_name))
            match ext:
                case ".sql":
                    __import_from_sql(conn, file)
                case ".csv":
                    dir = os.path.basename(os.path.normpath(subdir))
                    __import_from_csv(conn, file, name, dir)
                case _:
                    continue
    __update_delineations_srid("grid")


def downgrade() -> None:
    pass
