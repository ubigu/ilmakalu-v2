from meza import io
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine

from modules.config import Config

SCHEMA = "data"

cfg = Config("local_dev")
engine = create_engine(cfg.db_url())

current_path = Path(__file__).parent
infiles = [current_path / p for p in [ "ykr/T01_vae_e.mdb", "ykr/T03_tpa_e_TOL2008.mdb"]]

ykr = {}

for f in infiles:
    key = str(f).split("/")[-1]
    records = io.read(f)
    recs = []
    for r in records:
        recs.append(r)
    ykr[key] = recs

df_t01 = pd.DataFrame(ykr["T01_vae_e.mdb"])
df_t03 = pd.DataFrame(ykr["T03_tpa_e_TOL2008.mdb"])

employ = df_t03.copy()
employ = (
    employ.loc[:, ["xyind", "tp_yht", "kunta", "vuosi"]]
    .astype(dtype={"tp_yht": "Int32"})
    .reset_index(names="id")
)

pop = df_t01.copy()
pop = (
    pop.loc[:, ["xyind", "v_yht", "kunta", "vuosi"]]
    .astype(dtype={"v_yht": "Int32"})
    .reset_index(names="id")
)

tables = []

employ.to_sql("employ", engine, schema=SCHEMA, if_exists="replace", index=False)
tables.append((f"{SCHEMA}.employ", "id"))

pop.to_sql("pop", engine, schema=SCHEMA, if_exists="replace", index=False)
tables.append((f"{SCHEMA}.pop", "id"))

with engine.connect() as con:
    for table, column in tables:
        con.execute("ALTER TABLE {} ADD PRIMARY KEY ({});".format(table, column))
        con.execute("CREATE INDEX ON {} ({});".format(table, "kunta"))
        con.execute("CREATE INDEX ON {} ({});".format(table, "xyind"))
