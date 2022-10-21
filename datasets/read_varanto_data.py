from modules.varanto import EspooVaranto, VasaraVaranto
from pathlib import Path

ev = EspooVaranto()

filename = Path(__file__).parent / "dump_data/espoo_vasaramock.gpkg"
ev.init_from_mock_gpkg(filename , "espoo_vasaramock")

vv = VasaraVaranto()

v_filename = Path(__file__).parent / "dump_data/Vasara_2022-08-29T12_43_31.090Z.geojson"

vv.init_from_dump_json(v_filename)

pass
