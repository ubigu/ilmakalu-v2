from meza import io
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine

from modules.config import Config

cfg = Config("local_dev")
engine = create_engine(cfg.db_url())

current_path = Path(__file__).parent
infiles = [current_path / p for p in [ "ykr/T01_vae_e.mdb", "ykr/T03_tpa_e_TOL2008.mdb"]]#, "ykr/T16_vae_pat.mdb" ]]

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

# only required attributes are mapped to sensible data type
df_t01 = df_t01.astype(dtype={"v_yht": "Int32"})
df_t03 = df_t03.astype(dtype={"tp_yht": "Int32"})

v = df_t01.loc[:, ["xyind", "v_yht"]]
t = df_t03.loc[:, ["xyind", "tp_yht"]]

pop_emp = v.merge(t, how="outer", on="xyind").set_index("xyind")

pop_emp.to_sql("population_employment", engine, schema="data", if_exists="replace")
pass