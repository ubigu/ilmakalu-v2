"""Import data

Revision ID: 549fab520a40
Revises: fad8f477458f
Create Date: 2024-09-24 14:30:03.831130

"""

import os
from csv import DictReader
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "549fab520a40"
down_revision: Union[str, None] = "fad8f477458f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

tables = sqlmodel.SQLModel.metadata.tables
delimiter = ";"
encoding = "utf-8-sig"


def __import_from_sql(file, connection):
    try:
        with open(file) as f:
            stmt = sa.sql.text(f.read())
            with connection.begin_nested():
                connection.execute(stmt)
    except Exception:
        return


def __import_from_csv(file, name, schema, connection):
    """It is assumed that the file path follows
    the pattern '{root_dir}/{schema}/{table_name}.csv'"""
    table_name = f"{schema}.{name}"
    try:
        with open(file, encoding=encoding) as f:
            with connection.begin_nested():
                stmt = f"COPY {table_name} FROM STDIN DELIMITER '{delimiter}' CSV HEADER;"
                connection.connection.cursor().copy_expert(stmt, f)
    except Exception:
        # If COPY fails, try to insert rows one by one (this is slow)
        if table_name not in tables:
            return
        table = tables[table_name]
        with open(file, encoding=encoding) as f:
            for row in DictReader(f, skipinitialspace=True, delimiter=delimiter):
                try:
                    with connection.begin_nested():
                        connection.execute(table.insert().values({k: v for k, v in row.items()}))
                except Exception:
                    continue


def upgrade() -> None:
    connection = op.get_bind()
    root_dir = "database"
    for subdir, _, files in os.walk(root_dir):
        for file_name in files:
            file = os.path.join(subdir, file_name)
            print(f"Importing from file {file}...")
            name, ext = os.path.splitext(os.fsdecode(file_name))
            match ext:
                case ".sql":
                    __import_from_sql(file, connection)
                case ".csv":
                    dir = os.path.basename(os.path.normpath(subdir))
                    __import_from_csv(file, name, dir, connection)
                case _:
                    continue


def downgrade() -> None:
    pass
