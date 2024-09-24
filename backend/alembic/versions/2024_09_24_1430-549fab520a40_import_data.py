"""Import data

Revision ID: 549fab520a40
Revises: fad8f477458f
Create Date: 2024-09-24 14:30:03.831130

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = '549fab520a40'
down_revision: Union[str, None] = 'fad8f477458f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

import os
from csv import DictReader

tables = sqlmodel.SQLModel.metadata.tables
delimiter = ';'
encoding = 'utf-8-sig'

def import_data_from_csv(file, table_name):
    connection = op.get_bind()
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
    """ It is assumed that the paths follow
    the pattern '{root_dir}/{schema}/{table_name}.csv' """

    root_dir = 'database'
    schemas = next(os.walk(root_dir))[1]

    for schema in schemas:
        dir = os.path.join(root_dir, schema)
        for filename in os.listdir(dir):
            table_name, ext = os.path.splitext(os.fsdecode(filename))
            if not (ext == ".csv"): 
                continue
            table = f'{schema}.{table_name}'
            print(f'Importing data into table {table}...')
            import_data_from_csv(os.path.join(dir, filename), table)

def downgrade() -> None:
    pass
