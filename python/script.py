import psycopg2
import json
import requests

# Ask municipality code from user
# Develop further by creating a dict of name:code
#municipality_code = "KU" + input("Give municipality code in 3-number format (add leading zeros): ")
municipality_code = "KU091"

# Access and read JSON-query file produced in https://trafi2.stat.fi/PXWeb/pxweb/fi/TraFi/ from the same folder

with open("query.json", "r", encoding="utf-8") as file:
    content = file.read()
    query = json.loads(content)

# Replace municipality code with the user given
query['query'][0]['selection']['values'][0] = municipality_code

# Rather than owerwriting the original, create a new one with a different name
with open("query.json", 'w', encoding="utf-8") as file:
    file.write(json.dumps(query))
    
# Get JSON response by sending POST with json query
url = "https://trafi2.stat.fi:443/PXWeb/api/v1/fi/TraFi/Liikennekaytossa_olevat_ajoneuvot/010_kanta_tau_101.px"
session = requests.Session()
response = session.post(url, json=query)
response_json = json.loads(response.content.decode('utf-8-sig'))

# Create a dictionary for key value pairs
energy_modes = {}

# loop through the response and save to dictionary
for i in response_json['data']:
    key = i["key"][3]
    value = i["values"][0]
    if value == "-":
        energy_modes[key] = 0
    else:
        energy_modes[key] = value
    
# Check dictionary contents
print(energy_modes)

# Add dictionary contents to database
conn = psycopg2.connect("host=localhost dbname=postgres user=postgres password=Teemo90")


