from sqlmodel import SQLModel, Field
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import REAL, SMALLINT, VARCHAR

schema = 'grid_globals'

class buildings(SQLModel, table=True):
    __table_args__ = { "schema": schema }
    xyind: str = Field(sa_column=Column(VARCHAR(13), primary_key=True))
    rakv: int = Field(primary_key=True)
    energiam: str = Field(sa_column=Column(VARCHAR, primary_key=True))
    rakyht_lkm: int
    teoll_lkm: int
    varast_lkm: int
    rakyht_ala: float = Field(sa_column=Column(REAL))
    asuin_ala: float = Field(sa_column=Column(REAL))
    erpien_ala: float = Field(sa_column=Column(REAL))
    rivita_ala: float = Field(sa_column=Column(REAL))
    askert_ala: float = Field(sa_column=Column(REAL))
    liike_ala: float = Field(sa_column=Column(REAL))
    myymal_ala: float = Field(sa_column=Column(REAL))
    myymal_pien_ala: float = Field(sa_column=Column(REAL))
    myymal_super_ala: float = Field(sa_column=Column(REAL))
    myymal_hyper_ala: float = Field(sa_column=Column(REAL))
    myymal_muu_ala: float = Field(sa_column=Column(REAL))
    majoit_ala: float = Field(sa_column=Column(REAL))
    asla_ala: float = Field(sa_column=Column(REAL))
    ravint_ala: float = Field(sa_column=Column(REAL))
    tsto_ala: float = Field(sa_column=Column(REAL))
    liiken_ala: float = Field(sa_column=Column(REAL))
    hoito_ala: float = Field(sa_column=Column(REAL))
    kokoon_ala: float = Field(sa_column=Column(REAL))
    opetus_ala: float = Field(sa_column=Column(REAL))
    teoll_ala: float = Field(sa_column=Column(REAL))
    teoll_elint_ala: float = Field(sa_column=Column(REAL))
    teoll_tekst_ala: float = Field(sa_column=Column(REAL))
    teoll_puu_ala: float = Field(sa_column=Column(REAL))
    teoll_paper_ala: float = Field(sa_column=Column(REAL))
    teoll_miner_ala: float = Field(sa_column=Column(REAL))
    teoll_kemia_ala: float = Field(sa_column=Column(REAL))
    teoll_kone_ala: float = Field(sa_column=Column(REAL))
    teoll_mjalos_ala: float = Field(sa_column=Column(REAL))
    teoll_metal_ala: float = Field(sa_column=Column(REAL))
    teoll_vesi_ala: float = Field(sa_column=Column(REAL))
    teoll_energ_ala: float = Field(sa_column=Column(REAL))
    teoll_yhdysk_ala: float = Field(sa_column=Column(REAL))
    teoll_kaivos_ala: float = Field(sa_column=Column(REAL))
    teoll_muu_ala: float = Field(sa_column=Column(REAL))
    varast_ala: float = Field(sa_column=Column(REAL))
    muut_ala: float = Field(sa_column=Column(REAL))

class clc(SQLModel, table=True):
    __table_args__ = { "schema": schema }
    vuosi: int = Field(primary_key=True)
    kunta: str = Field(primary_key=True)
    maa_ha: float = Field(sa_column=Column(REAL))
    vesi_ha: float
    clc1111: float
    clc1121: float
    clc1211: float
    clc1212: float
    clc1221: float
    clc1231: float
    clc1241: float
    clc1311: float
    clc1312: float
    clc1321: float
    clc1331: float
    clc1411: float
    clc1421: float
    clc1422: float
    clc1423: float
    clc1424: float
    clc2111: float
    clc2221: float
    clc2311: float
    clc2312: float
    clc2431: float
    clc2441: float
    clc3111: float
    clc3112: float
    clc3121: float
    clc3122: float
    clc3123: float
    clc3131: float
    clc3132: float
    clc3133: float
    clc3211: float
    clc3221: float
    clc3241: float
    clc3242: float
    clc3243: float
    clc3244: float
    clc3246: float
    clc3311: float
    clc3321: float
    clc3331: float
    clc4111: float
    clc4112: float
    clc4121: float
    clc4122: float
    clc4211: float
    clc4212: float
    clc5111: float
    clc5121: float
    clc5231: float
    xyind: str = Field(sa_column=Column(VARCHAR(13), primary_key=True))

class employ(SQLModel, table=True):
    __table_args__ = { "schema": schema }
    vuosi: int = Field(primary_key=True)
    kunta: int = Field(primary_key=True)
    tp_yht: int = Field(sa_column=Column(SMALLINT))
    xyind: str = Field(sa_column=Column(VARCHAR(13), primary_key=True))

class pop(SQLModel, table=True):
    __table_args__ = { "schema": schema }
    vuosi: int = Field(primary_key=True)
    kunta: int = Field(primary_key=True)
    xyind: str = Field(sa_column=Column(VARCHAR(13), primary_key=True))
    v_yht: int = Field(sa_column=Column(SMALLINT))
    v_0_6: int = Field(sa_column=Column(SMALLINT))
    v_7_14: int = Field(sa_column=Column(SMALLINT))
    v_15_17: int = Field(sa_column=Column(SMALLINT))
    v_18_29: int = Field(sa_column=Column(SMALLINT))
    v_30_49: int = Field(sa_column=Column(SMALLINT))
    v_50_64: int = Field(sa_column=Column(SMALLINT))
    v_65_74: int = Field(sa_column=Column(SMALLINT))
    v_75: int = Field(sa_column=Column(SMALLINT))