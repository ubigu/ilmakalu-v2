import psycopg2
import json
import requests
from config.credentials import Config

# Create a config object
cfg = Config()
cfg.user_credentials('database')

'''
Käyttövoimakoodit:
- Bensiini = 01
- Diesel = 02
- Polttoöljy = 03
- Sähkö = 04
- Vety = 05
- Kaasu = 06
- Nestekaasu (LPG) = 11
- Maakaasu (CNG) = 13
- Bensiini/Puu = 33
- Bensiini + moottoripetroli = 34
- Etanoli = 37
- Bensiini/CNG = 38
- Bensiini/Sähkö (ladattava hybridi) = 39
- Bensiini/Etanoli = 40
- Bensiini/Metanoli = 41
- Bensiini/LPG = 42
- Diesel/CNG = 43
- Diesel/Sähkö (ladattava hybridi) = 44
- Muu = Y
- Yhteensä = YH
'''

# Ask municipality code from user
mun_code = int(input("Give municipality code: "))

# Access and read passenger car JSON-query file produced in https://trafi2.stat.fi/PXWeb/pxweb/fi/TraFi/ from the same folder
with open("passenger_car_query.json", "r", encoding="utf-8") as file:
    content = file.read()
    query = json.loads(content)

# Replace municipality code with the user given to passenger car JSON query
json_mun_code = ""
if len(str(mun_code)) == 1:
    json_mun_code = "KU00" + str(mun_code)
elif len(str(mun_code)) == 2:
    json_mun_code = "KU0" + str(mun_code)
else:
    json_mun_code = "KU" + str(mun_code)

print(json_mun_code)

query['query'][0]['selection']['values'][0] = json_mun_code

# Rewrite the passenger car energy mode distribution JSON query file
with open("passenger_car_query.json", 'w', encoding="utf-8") as file:
    file.write(json.dumps(query))
    
# Get passenger car JSON response (POST with edited JSON query)
url = "https://trafi2.stat.fi:443/PXWeb/api/v1/fi/TraFi/Liikennekaytossa_olevat_ajoneuvot/010_kanta_tau_101.px"
session = requests.Session()
response = session.post(url, json=query)
response_json = json.loads(response.content.decode('utf-8-sig'))
#print(response_json)

# Create a initial dictionary for key value pairs for passenger cars
energy_modes_init = {}

# loop through the response and save energy mode values to dictionary for passenger cars
for i in response_json['data']:
    key = i["key"][3]
    value = i["values"][0]
    if value == "-":
        energy_modes_init[key] = 0
    else:
        energy_modes_init[key] = value

# Check initial dictionary contents
#print(energy_modes_init)

# Create a refined dictionary with proper key names, energy mode combinations and proportional shares for passenger cars
energy_modes_ref = {}
energy_modes_ref["kvoima_bensiini"] = int(energy_modes_init["01"]) / int(energy_modes_init["YH"])
energy_modes_ref["kvoima_diesel"] = int(energy_modes_init["02"]) / int(energy_modes_init["YH"])
energy_modes_ref["kvoima_etanoli"] = int(energy_modes_init["37"]) / int(energy_modes_init["YH"])
energy_modes_ref["kvoima_kaasu"] = (int(energy_modes_init["06"]) + int(energy_modes_init["11"]) + int(energy_modes_init["13"])) / int(energy_modes_init["YH"])
energy_modes_ref["kvoima_phev_b"] = int(energy_modes_init["39"]) / int(energy_modes_init["YH"])
energy_modes_ref["kvoima_phev_d"] = int(energy_modes_init["44"]) / int(energy_modes_init["YH"])
energy_modes_ref["kvoima_ev"] = int(energy_modes_init["04"]) / int(energy_modes_init["YH"])
energy_modes_ref["kvoima_vety"] = int(energy_modes_init["05"]) / int(energy_modes_init["YH"])
energy_modes_ref["kvoima_muut"] = (int(energy_modes_init["33"]) + int(energy_modes_init["34"]) + int(energy_modes_init["38"]) + int(energy_modes_init["40"]) + int(energy_modes_init["41"]) + int(energy_modes_init["42"]) + int(energy_modes_init["43"]) + int(energy_modes_init["Y"])) / int(energy_modes_init["YH"])

# Check refined dictionary contents
print(energy_modes_ref)

# Add dictionary contents to database

# Connect to database
try:
    conn = psycopg2.connect(cfg.postgresql_string())
except: 
    raise Exception("Couldn't connect to database")

cursor = conn.cursor()

# Create a new table
cursor.execute("DROP TABLE IF EXISTS energy_modes")
create_table ='''CREATE TABLE energy_modes(
   id SERIAL PRIMARY KEY,
   mun INT4,
   scenario VARCHAR,
   year INT4,
   kmuoto VARCHAR,
   kvoima_bensiini DECIMAL(10,3),
   kvoima_diesel DECIMAL(10,3),
   kvoima_etanoli DECIMAL(10,3),
   kvoima_kaasu DECIMAL(10,3),
   kvoima_phev_b DECIMAL(10,3),
   kvoima_phev_d DECIMAL(10,3),
   kvoima_ev DECIMAL(10,3),
   kvoima_vety DECIMAL(10,3),
   kvoima_muut DECIMAL(10,3)
)'''
cursor.execute(create_table)

# Insert passenger cars
insert_into = ("""INSERT INTO energy_modes(mun, scenario, year, kmuoto , kvoima_bensiini, kvoima_diesel, kvoima_etanoli, kvoima_kaasu, kvoima_phev_b, kvoima_phev_d, 
              kvoima_ev, kvoima_vety, kvoima_muut) 
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""")
cursor.execute(insert_into, (mun_code, 'wem', 2021, 'hlauto', energy_modes_ref["kvoima_bensiini"], energy_modes_ref["kvoima_diesel"], energy_modes_ref["kvoima_etanoli"], 
              energy_modes_ref["kvoima_kaasu"], energy_modes_ref["kvoima_phev_b"], energy_modes_ref["kvoima_phev_d"], energy_modes_ref["kvoima_ev"],
              energy_modes_ref["kvoima_vety"], energy_modes_ref["kvoima_muut"]))


# Insert walking and biking
insert_into = ("""INSERT INTO energy_modes(mun, scenario, year, kmuoto , kvoima_bensiini, kvoima_diesel, kvoima_etanoli, kvoima_kaasu, kvoima_phev_b, kvoima_phev_d, 
              kvoima_ev, kvoima_vety, kvoima_muut) 
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""")
cursor.execute(insert_into, (mun_code, 'wem', 2021,'jalkapyora', 0, 0, 0, 0, 0, 0, 0, 0, 0))


# Insert other modes of transport
insert_into = ("""INSERT INTO energy_modes(mun, scenario, year, kmuoto , kvoima_bensiini, kvoima_diesel, kvoima_etanoli, kvoima_kaasu, kvoima_phev_b, kvoima_phev_d, 
              kvoima_ev, kvoima_vety, kvoima_muut) 
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""")
cursor.execute(insert_into, (mun_code, 'wem', 2021,'muu', 0, 0, 0, 0, 0, 0, 0, 0, 1))

# Insert rail
insert_into = ("""INSERT INTO energy_modes(mun, scenario, year, kmuoto , kvoima_bensiini, kvoima_diesel, kvoima_etanoli, kvoima_kaasu, kvoima_phev_b, kvoima_phev_d, 
              kvoima_ev, kvoima_vety, kvoima_muut) 
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""")
cursor.execute(insert_into, (mun_code, 'wem', 2021,'raide', 0, 0, 0, 0, 0, 0, 1, 0, 0))


# Finalize
conn.commit()
cursor.close()
conn.close()