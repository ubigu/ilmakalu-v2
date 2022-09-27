import json
import requests
from modules.config import Config
from sqlalchemy import create_engine

'''
This script gets building CO2 costs related to different stages
of a building life cycle. Three different resource types exits:
materials, processes and scenarios. This script catches only
materials and their specified attributes. 

Specify initial data URL in config.yaml. 

See more at www.co2data.fi.
'''

# get service url
cfg = Config()
url = cfg.co2dataurl()

# create session and save response
session = requests.Session()
response = session.post(url)

# load response content as json
response_json = json.loads(response.content.decode('utf-8-sig'))

# dump json to file for inspection if needed
'''
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(response_json, f, ensure_ascii=False, indent=4)
'''

# Loop json and catch materials
materials = {}

for i in range(len(response_json["Resources"])):
    key = response_json["Resources"][i]["ResourceId"]
    if response_json["Resources"][i]["ResourceType"] == "Material":
        materials[key] = []
        materials[key].append(response_json["Resources"][i]["Name"])
        materials[key].append(response_json["Resources"][i]["DataItems"]["DataValueItems"][0]["Value"])
        materials[key].append(response_json["Resources"][i]["DataItems"]["DataValueItems"][1]["Value"])
        materials[key].append(response_json["Resources"][i]["WasteFactor"])
        materials[key].append(response_json["Resources"][i]["RefServiceLifeNormal"])

        # check conversion value more accurately since it might not exist or might be a string instead of a number
        conversion = response_json["Resources"][i]["Conversions"]
        if len(conversion) == 0:
            materials[key].append(None)
        elif type(conversion[0]["Value"]) == str:
            materials[key].append(None)
        else:
            materials[key].append(conversion[0]["Value"])
        
        # check eols reuse value more accurately since it might not exist or might be a string instead of a number
        eols_reuse = response_json["Resources"][i]["Material"]["End of life scenario"]["Reuse"]
        if type(eols_reuse) == str or type(eols_reuse) is None:
            materials[key].append(0)
        else:
            materials[key].append(eols_reuse)
        
        # check eols recycled value more accurately since it might not exist or might be a string instead of a number
        eols_recycled = response_json["Resources"][i]["Material"]["End of life scenario"]["Recycled"]
        if type(eols_recycled) == str or type(eols_recycled) is None:
            materials[key].append(0)
        else:
            materials[key].append(eols_recycled)

        # check eols energy value more accurately since it might not exist or might be a string instead of a number
        eols_energy = response_json["Resources"][i]["Material"]["End of life scenario"]["Energy"]
        if type(eols_energy) == str or type(eols_energy) is None:
            materials[key].append(0)
        else:
            materials[key].append(eols_energy)

        # check eols final value more accurately since it might not exist or might be a string instead of a number
        eols_final = response_json["Resources"][i]["Material"]["End of life scenario"]["Final"]
        if type(eols_final) == str or type(eols_final) is None:
            materials[key].append(0)
        else:
            materials[key].append(eols_final)

# initialize postgres connection
pg_connection = create_engine(cfg._db_connection_url())

# create table in postgres for materials gwp
create_materials_table =''' 
            CREATE TABLE data.building_materials_gwp(
            resourceid BIGINT PRIMARY KEY,
            name TEXT,
            gwp_conservative DECIMAL(10,2),
            gwp_typical DECIMAL(10,2),
            waste_factor DECIMAL(10,2),
            service_life TEXT,
            conversion_value DECIMAL(10,2),
            eols_reuse DECIMAL(10,2),
            eols_recycled DECIMAL(10,2),
            eols_energy DECIMAL(10,2),
            eols_final DECIMAL(10,2)
            )'''

try:
    with pg_connection.connect() as con:
        con.execute('''DROP TABLE IF EXISTS data.building_materials_gwp''')
except:
        raise RuntimeError("Couldn't execute DROP TABLE for building materials gwp")

try:
    with pg_connection.connect() as con:
        con.execute(create_materials_table)
except:
        raise RuntimeError("Couldn't create the table for building materials gwp")

# push materials from dictionary to the table
insert_into_materials = ("""INSERT INTO data.building_materials_gwp(resourceid, name, gwp_conservative, gwp_typical,waste_factor,service_life,conversion_value,eols_reuse,eols_recycled,eols_energy,eols_final) 
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""")

for key, values in materials.items():
    with pg_connection.connect() as con:
        con.execute(insert_into_materials, (key,values[0],values[1],values[2],values[3],values[4],values[5],values[6],values[7],values[8],values[9]))
