import psycopg2
import json
import requests
from config.credentials import Config
from area_code_handler import mun_code_handler, reg_code_handler

# Create a config object
cfg = Config()
cfg.user_credentials('database')

# Ask municipality code from user
mun_code = int(input("Give municipality code: "))

# Ask region code from user
reg_code = int(input("Give region code: "))

# Access and read preloaded JSON queries retrieved from https://trafi2.stat.fi/
with open("passenger_cars_query.json", "r", encoding="utf-8") as passenger_cars, open("heavy_cars_query.json", "r", encoding="utf-8") as heavy_cars:
    passenger_cars_content = passenger_cars.read()
    passenger_cars_query = json.loads(passenger_cars_content)

    heavy_cars_content = heavy_cars.read()
    heavy_cars_query = json.loads(heavy_cars_content)

# Replace area codes to both queries
passenger_cars_query['query'][0]['selection']['values'][0] = mun_code_handler(mun_code)
heavy_cars_query['query'][0]['selection']['values'][0] = reg_code_handler(reg_code)

# Rewrite both JSON queries <-- This needs to be replaced so we retain original JSON files
with open("passenger_cars_query.json", 'w', encoding="utf-8") as passenger_cars_rewrite, open("heavy_cars_query.json", "w", encoding="utf-8") as heavy_cars_rewrite:
    passenger_cars_rewrite.write(json.dumps(passenger_cars_query))
    heavy_cars_rewrite.write(json.dumps(heavy_cars_query))

# Get passenger car JSON response (POST with edited JSON query)
url_passenger_cars = "https://trafi2.stat.fi:443/PXWeb/api/v1/fi/TraFi/Liikennekaytossa_olevat_ajoneuvot/010_kanta_tau_101.px"
url_heavy_cars = "https://trafi2.stat.fi:443/PXWeb/api/v1/fi/TraFi/Liikennekaytossa_olevat_ajoneuvot/040_kanta_tau_104.px"

session = requests.Session()

response_passenger_cars = session.post(url_passenger_cars, json=passenger_cars_query)
response_heavy_cars = session.post(url_heavy_cars, json=heavy_cars_query)

response_json_passenger_cars = json.loads(response_passenger_cars.content.decode('utf-8-sig'))
response_json_heavy_cars = json.loads(response_heavy_cars.content.decode('utf-8-sig'))

#print("PASSENGER CARS:")
#print(response_json_passenger_cars)
#print("HEAVY CARS:")
#print(response_json_heavy_cars)

# Create a initial dictionaries for parsing JSON responses
passenger_cars_energy_modes = {}
heavy_cars_energy_modes = {}

# loop through responses and save energy mode values to dictionary
# passenger cars
for i in response_json_passenger_cars['data']:
    key = i["key"][3]
    value = i["values"][0]
    if value == "-":
        passenger_cars_energy_modes[key] = 0
    else:
        passenger_cars_energy_modes[key] = value

# heavy cars <-- here the fact that stats are by a quarter requires aggregation
# This is still a direct copy from passenger cars and won't produce correct results
# it won't give an error though, just wrong result
for i in response_json_heavy_cars['data']:
    key = i["key"][3]
    value = i["values"][0]
    if value == "-":
        heavy_cars_energy_modes[key] = 0
    else:
        heavy_cars_energy_modes[key] = value

# Check initial dictionary contents
#print(passenger_cars_energy_modes)
#print(heavy_cars_energy_modes)

# Create a refined dictionary with proper key names, energy mode combinations and proportional shares for passenger cars
passenger_car_energy_modes_ref = {}
passenger_car_energy_modes_ref["kvoima_bensiini"] = int(passenger_cars_energy_modes["01"]) / int(passenger_cars_energy_modes["YH"])
passenger_car_energy_modes_ref["kvoima_diesel"] = int(passenger_cars_energy_modes["02"]) / int(passenger_cars_energy_modes["YH"])
passenger_car_energy_modes_ref["kvoima_etanoli"] = int(passenger_cars_energy_modes["37"]) / int(passenger_cars_energy_modes["YH"])
passenger_car_energy_modes_ref["kvoima_kaasu"] = (int(passenger_cars_energy_modes["06"]) + int(passenger_cars_energy_modes["11"]) + int(passenger_cars_energy_modes["13"])) / int(passenger_cars_energy_modes["YH"])
passenger_car_energy_modes_ref["kvoima_phev_b"] = int(passenger_cars_energy_modes["39"]) / int(passenger_cars_energy_modes["YH"])
passenger_car_energy_modes_ref["kvoima_phev_d"] = int(passenger_cars_energy_modes["44"]) / int(passenger_cars_energy_modes["YH"])
passenger_car_energy_modes_ref["kvoima_ev"] = int(passenger_cars_energy_modes["04"]) / int(passenger_cars_energy_modes["YH"])
passenger_car_energy_modes_ref["kvoima_vety"] = int(passenger_cars_energy_modes["05"]) / int(passenger_cars_energy_modes["YH"])
passenger_car_energy_modes_ref["kvoima_muut"] = (int(passenger_cars_energy_modes["33"]) + int(passenger_cars_energy_modes["34"]) + int(passenger_cars_energy_modes["38"]) + int(passenger_cars_energy_modes["40"]) + int(passenger_cars_energy_modes["41"]) + int(passenger_cars_energy_modes["42"]) + int(passenger_cars_energy_modes["43"]) + int(passenger_cars_energy_modes["Y"])) / int(passenger_cars_energy_modes["YH"])

# Check refined dictionary contents
#print(energy_modes_ref)


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
cursor.execute(insert_into, (mun_code, 'wem', 2021, 'hlauto', passenger_car_energy_modes_ref["kvoima_bensiini"], passenger_car_energy_modes_ref["kvoima_diesel"], passenger_car_energy_modes_ref["kvoima_etanoli"], 
              passenger_car_energy_modes_ref["kvoima_kaasu"], passenger_car_energy_modes_ref["kvoima_phev_b"], passenger_car_energy_modes_ref["kvoima_phev_d"], passenger_car_energy_modes_ref["kvoima_ev"],
              passenger_car_energy_modes_ref["kvoima_vety"], passenger_car_energy_modes_ref["kvoima_muut"]))


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

# Tell user that no errors were encountered
print()
print("No errors, check Postgres localhost")
print()