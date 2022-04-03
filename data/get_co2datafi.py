import json
import requests
from database_handler import create_table, insert_data


url = "https://co2data.fi/api/co2data_construction.json"

# get json file
session = requests.Session()
response = session.post(url)

# create output dictionary for gwp values (both materials and processes)
gwp_values = {}

# get JSON response from the SYKE service
response_json = json.loads(response.content.decode('utf-8-sig'))


# loop through the response
# for now we take only materials and exclude processes due to processes not having always two gwp values in 'DataValueItems'
for i in range(len(response_json["Resources"])):
    if response_json["Resources"][i]["ResourceType"] == "Material":
        gwp_values[response_json["Resources"][i]["ResourceId"]] = []
        gwp_values[response_json["Resources"][i]["ResourceId"]].append(response_json["Resources"][i]["Name"])
        gwp_values[response_json["Resources"][i]["ResourceId"]].append(response_json["Resources"][i]["ResourceType"])
        gwp_values[response_json["Resources"][i]["ResourceId"]].append(response_json["Resources"][i]["DataItems"]["DataValueItems"][0]["Value"])
        gwp_values[response_json["Resources"][i]["ResourceId"]].append(response_json["Resources"][i]["DataItems"]["DataValueItems"][1]["Value"])

#print(gwp_values)

# push parsed contents to postgres. Try to use same database_handler.py
# before doing this it would be better to create initial schema in pg data modeler, let's not create tables here unnecessary