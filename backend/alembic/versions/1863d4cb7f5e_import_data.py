"""Import data

Revision ID: 1863d4cb7f5e
Revises: 30e2e5e7b557
Create Date: 2024-09-16 13:07:18.355532

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import os

# revision identifiers, used by Alembic.
revision: str = '1863d4cb7f5e'
down_revision: Union[str, None] = '30e2e5e7b557'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def import_data_from_csv(connection, file, table_name):
    try:
        with open(file, encoding='utf-8-sig') as f:
            with connection.begin_nested():
                cmd = f"COPY {table_name} FROM STDIN DELIMITER ';' CSV HEADER;"
                connection.connection.cursor().copy_expert(cmd, f)
                connection.commit()
    except:
        """# If COPY fails, try to insert rows one by one (this is slow)
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
                continue"""

def upgrade() -> None:
    """ It is assumed that the paths follow
    the pattern '{root_dir}/{schema}/{table_name}.csv' """

    connection = op.get_bind()
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
            import_data_from_csv(connection, os.path.join(dir, filename), table)

def downgrade() -> None:
    pass
