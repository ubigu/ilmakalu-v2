import json
import requests
from area_code_handler import mun_code_handler, reg_code_handler
from database_handler import create_table, insert_passenger_cars, insert_walking_biking, insert_rail, insert_vans, insert_trucks, insert_busses, insert_others, insert_data

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

# Save heavy cars json response for dev purposes
#with open("heavy_cars_json_response.json", "w", encoding="utf-8") as file:
#    file.write(json.dumps(response_json_heavy_cars))

# loop through responses and save energy mode values to dictionary
# passenger cars
passenger_cars_energy_modes = {}

for i in response_json_passenger_cars['data']:
    key = i["key"][3]
    if i["values"][0] == "-":
        value = 0
    else:
        value = i["values"][0]
    
    passenger_cars_energy_modes[key] = value


# heavy cars: dictionary where key is transport mode (02, 03, 04)...
# ...and value is another dictionary with fuel type and count
heavy_cars_energy_modes = {"02":{},"03":{},"04":{}}

# Better to loop through all the values first and change "-" with 0?
for i in response_json_heavy_cars['data']:
    transport_mode = i["key"][1] # get transport mode
    fuel = i["key"][2] # get fuel type
    
    # get the actual value
    if i["values"][0] == "-":
        value = 0
    else:
        value = int(i["values"][0])

    #print(i)
    #print(transport_mode)
    #print(fuel)
    #print(value)
    
    if fuel not in heavy_cars_energy_modes[transport_mode]:
        heavy_cars_energy_modes[transport_mode][fuel] = value
    else:
        heavy_cars_energy_modes[transport_mode][fuel] += value

# Check initial dictionary contents
#print(passenger_cars_energy_modes)
#print(heavy_cars_energy_modes)

# Create refined dictionary for passenger cars
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
print()
print("Passenger cars:")
print(passenger_car_energy_modes_ref)
print()

# Create refined dictionary for vans
vans_energy_modes_ref = {}
vans_energy_modes_ref["kvoima_bensiini"] = int(heavy_cars_energy_modes["02"]["01"]) / int(heavy_cars_energy_modes["02"]["YH"])
vans_energy_modes_ref["kvoima_diesel"] = (int(heavy_cars_energy_modes["02"]["02"]) + int(heavy_cars_energy_modes["02"]["10"])) / int(heavy_cars_energy_modes["02"]["YH"])
vans_energy_modes_ref["kvoima_etanoli"] = int(heavy_cars_energy_modes["02"]["37"]) / int(heavy_cars_energy_modes["02"]["YH"])
vans_energy_modes_ref["kvoima_kaasu"] = (int(heavy_cars_energy_modes["02"]["06"]) + int(heavy_cars_energy_modes["02"]["11"]) + int(heavy_cars_energy_modes["02"]["13"]) + int(heavy_cars_energy_modes["02"]["56"]) + int(heavy_cars_energy_modes["02"]["65"])) / int(heavy_cars_energy_modes["02"]["YH"])
vans_energy_modes_ref["kvoima_phev_b"] = int(heavy_cars_energy_modes["02"]["39"]) / int(heavy_cars_energy_modes["02"]["YH"])
vans_energy_modes_ref["kvoima_phev_d"] = int(heavy_cars_energy_modes["02"]["44"]) / int(heavy_cars_energy_modes["02"]["YH"])
vans_energy_modes_ref["kvoima_ev"] = int(heavy_cars_energy_modes["02"]["04"]) / int(heavy_cars_energy_modes["02"]["YH"])
vans_energy_modes_ref["kvoima_vety"] = int(heavy_cars_energy_modes["02"]["05"]) / int(heavy_cars_energy_modes["02"]["YH"])
vans_energy_modes_ref["kvoima_muut"] = (int(heavy_cars_energy_modes["02"]["03"]) + int(heavy_cars_energy_modes["02"]["31"]) + int(heavy_cars_energy_modes["02"]["33"]) + int(heavy_cars_energy_modes["02"]["34"]) + int(heavy_cars_energy_modes["02"]["38"]) + int(heavy_cars_energy_modes["02"]["40"]) + int(heavy_cars_energy_modes["02"]["42"]) + int(heavy_cars_energy_modes["02"]["43"]) + int(heavy_cars_energy_modes["02"]["67"]) + int(heavy_cars_energy_modes["02"]["Y"])) / int(heavy_cars_energy_modes["02"]["YH"])
print("Vans:")
print(vans_energy_modes_ref)
print()

# Create refined dictionary for trucks
trucks_energy_modes_ref = {}
trucks_energy_modes_ref["kvoima_bensiini"] = int(heavy_cars_energy_modes["03"]["01"]) / int(heavy_cars_energy_modes["03"]["YH"])
trucks_energy_modes_ref["kvoima_diesel"] = (int(heavy_cars_energy_modes["03"]["02"]) + int(heavy_cars_energy_modes["03"]["10"])) / int(heavy_cars_energy_modes["03"]["YH"])
trucks_energy_modes_ref["kvoima_etanoli"] = int(heavy_cars_energy_modes["03"]["37"]) / int(heavy_cars_energy_modes["03"]["YH"])
trucks_energy_modes_ref["kvoima_kaasu"] = (int(heavy_cars_energy_modes["03"]["06"]) + int(heavy_cars_energy_modes["03"]["11"]) + int(heavy_cars_energy_modes["03"]["13"]) + int(heavy_cars_energy_modes["03"]["56"]) + int(heavy_cars_energy_modes["03"]["65"])) / int(heavy_cars_energy_modes["03"]["YH"])
trucks_energy_modes_ref["kvoima_phev_b"] = int(heavy_cars_energy_modes["03"]["39"]) / int(heavy_cars_energy_modes["03"]["YH"])
trucks_energy_modes_ref["kvoima_phev_d"] = int(heavy_cars_energy_modes["03"]["44"]) / int(heavy_cars_energy_modes["03"]["YH"])
trucks_energy_modes_ref["kvoima_ev"] = int(heavy_cars_energy_modes["03"]["04"]) / int(heavy_cars_energy_modes["03"]["YH"])
trucks_energy_modes_ref["kvoima_vety"] = int(heavy_cars_energy_modes["03"]["05"]) / int(heavy_cars_energy_modes["03"]["YH"])
trucks_energy_modes_ref["kvoima_muut"] = (int(heavy_cars_energy_modes["03"]["03"]) + int(heavy_cars_energy_modes["03"]["31"]) + int(heavy_cars_energy_modes["03"]["33"]) + int(heavy_cars_energy_modes["03"]["34"]) + int(heavy_cars_energy_modes["03"]["38"]) + int(heavy_cars_energy_modes["03"]["40"]) + int(heavy_cars_energy_modes["03"]["42"]) + int(heavy_cars_energy_modes["03"]["43"]) + int(heavy_cars_energy_modes["03"]["67"]) + int(heavy_cars_energy_modes["03"]["Y"])) / int(heavy_cars_energy_modes["03"]["YH"])
print("Trucks:")
print(trucks_energy_modes_ref)
print()

# Create refined dictionary for busses
busses_energy_modes_ref = {}
busses_energy_modes_ref["kvoima_bensiini"] = int(heavy_cars_energy_modes["04"]["01"]) / int(heavy_cars_energy_modes["04"]["YH"])
busses_energy_modes_ref["kvoima_diesel"] = (int(heavy_cars_energy_modes["04"]["02"]) + int(heavy_cars_energy_modes["04"]["10"])) / int(heavy_cars_energy_modes["04"]["YH"])
busses_energy_modes_ref["kvoima_etanoli"] = int(heavy_cars_energy_modes["04"]["37"]) / int(heavy_cars_energy_modes["04"]["YH"])
busses_energy_modes_ref["kvoima_kaasu"] = (int(heavy_cars_energy_modes["04"]["06"]) + int(heavy_cars_energy_modes["04"]["11"]) + int(heavy_cars_energy_modes["04"]["13"]) + int(heavy_cars_energy_modes["04"]["56"]) + int(heavy_cars_energy_modes["04"]["65"])) / int(heavy_cars_energy_modes["04"]["YH"])
busses_energy_modes_ref["kvoima_phev_b"] = int(heavy_cars_energy_modes["04"]["39"]) / int(heavy_cars_energy_modes["04"]["YH"])
busses_energy_modes_ref["kvoima_phev_d"] = int(heavy_cars_energy_modes["04"]["44"]) / int(heavy_cars_energy_modes["04"]["YH"])
busses_energy_modes_ref["kvoima_ev"] = int(heavy_cars_energy_modes["04"]["04"]) / int(heavy_cars_energy_modes["04"]["YH"])
busses_energy_modes_ref["kvoima_vety"] = int(heavy_cars_energy_modes["04"]["05"]) / int(heavy_cars_energy_modes["04"]["YH"])
busses_energy_modes_ref["kvoima_muut"] = (int(heavy_cars_energy_modes["04"]["03"]) + int(heavy_cars_energy_modes["04"]["31"]) + int(heavy_cars_energy_modes["04"]["33"]) + int(heavy_cars_energy_modes["04"]["34"]) + int(heavy_cars_energy_modes["04"]["38"]) + int(heavy_cars_energy_modes["04"]["40"]) + int(heavy_cars_energy_modes["04"]["42"]) + int(heavy_cars_energy_modes["04"]["43"]) + int(heavy_cars_energy_modes["04"]["67"]) + int(heavy_cars_energy_modes["04"]["Y"])) / int(heavy_cars_energy_modes["04"]["YH"])
print("Busses:")
print(busses_energy_modes_ref)
print()

# Create table by calling database handler module
create_table()

# insert passenger cars to the table
insert_data(mun_code, "passenger car", passenger_car_energy_modes_ref)

# insert vans into the table
insert_data(mun_code, "van", vans_energy_modes_ref)

# insert trucks into the table
insert_data(mun_code, "truck", trucks_energy_modes_ref)

# insert walking and biking into the table
insert_walking_biking(mun_code)

# insert rail into the table
insert_rail(mun_code)

# insert busses into the table
insert_busses(mun_code, busses_energy_modes_ref)

# insert other modes of transport into the table
insert_others(mun_code)

# Tell user that no errors were encountered
print()
print("No errors, check Postgres localhost")
print()