import json
import requests
from database_handler import create_table, insert_data


url = "https://co2data.fi/api/co2data_construction.json"

# get json file
session = requests.Session()
response = session.post(url)


# Make this into a loop to a dictionary
response_json = json.loads(response.content.decode('utf-8-sig'))
print("Resource ID:")
print(response_json["Resources"][0]["ResourceId"])
print()
print(response_json["Resources"][0]["Name"])
print()
print("Conservative GWP:")
print(response_json["Resources"][0]["DataItems"]["DataValueItems"][0]["Value"])
print()
print("Typical GWP:")
print(response_json["Resources"][0]["DataItems"]["DataValueItems"][1]["Value"])

# parse the above dictionary as/if needed


# push parsed contents to postgres. Try to use same database_handler.py