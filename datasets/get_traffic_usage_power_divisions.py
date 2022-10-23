import json
import requests
from modules.config import Config
from sqlalchemy import create_engine
import pandas as pd

# initialize config module
cfg = Config()
pg_connection = create_engine(cfg._db_connection_url())

# create session and get responses from traficom statistics service
session = requests.Session()    
response_passenger_cars = session.post(cfg.traficom_passenger_cars_usage_modes_url(), json=cfg.traficom_json_query_for_passenger_car_usage_modes())
response_heavy_cars = session.post(cfg.traficom_heavy_cars_usage_modes_url(), json=cfg.traficom_json_query_for_heavy_car_usage_modes())

# tranform responses to json
response_json_passenger_cars = json.loads(response_passenger_cars.content.decode('utf-8-sig'))
response_json_heavy_cars = json.loads(response_heavy_cars.content.decode('utf-8-sig'))

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

# a dictionary for heavy cars where key is transport mode and value is another dictionary with fuel type and count
modes = cfg.traficom_heavy_car_types_in_usage_mode()
heavy_cars_energy_modes = {modes[0]:{},modes[1]:{},modes[2]:{}}

# loop through all the values first and change "-" with 0
for i in response_json_heavy_cars['data']:
    transport_mode = i["key"][1] # get transport mode
    fuel = i["key"][2] # get fuel type
    
    # get the actual value
    if i["values"][0] == "-":
        value = 0
    else:
        value = int(i["values"][0])

    if fuel not in heavy_cars_energy_modes[transport_mode]:
        heavy_cars_energy_modes[transport_mode][fuel] = value
    else:
        heavy_cars_energy_modes[transport_mode][fuel] += value

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

# convert dictionaries to dataframes. Add index because values are scalar. 
df_passenger_cars = pd.DataFrame(passenger_car_energy_modes_ref,index=[0])
df_passenger_cars['kmuoto'] = 'hlauto'

df_vans = pd.DataFrame(vans_energy_modes_ref,index=[0])
df_vans['kmuoto'] = 'pauto'

df_trucks = pd.DataFrame(trucks_energy_modes_ref,index=[0])
df_trucks['kmuoto'] = 'kauto'

df_busses = pd.DataFrame(busses_energy_modes_ref,index=[0])
df_busses['kmuoto'] = 'bussi'

# merge above dataframes with reseted index
df_vehicles = pd.concat([df_passenger_cars,df_vans,df_trucks,df_busses]).reset_index(drop=True)

# add remaining traffic modes having static values
other_traffic_modes =  {
        "kvoima_bensiini":[0,0,0],"kvoima_diesel":[0,0,0],"kvoima_etanoli":[0,0,0],"kvoima_kaasu":[0,0,0],"kvoima_phev_b":[0,0,0],
        "kvoima_phev_d":[0,0,0],"kvoima_ev":[1,0,0],"kvoima_vety":[0,0,0],"kvoima_muut":[0,0,1],"kmuoto":["raide","jalkapyora","muu"]
        }
        
df_all = pd.concat([df_vehicles,pd.DataFrame(other_traffic_modes)]).reset_index(drop=True)

# add year
df_all["year"] = 2021

# add scenario
df_all["scenario"] = 'wem'

# add municipality code
df_all["mun"] = int(cfg.traficom_municipality_code()[-3:])

# add one to index so that identity column in postgres doesn't start from zero
df_all.index += 1

# round decimals
df_all = df_all.round(decimals=3)

print(df_all)

# accuracy of decimal fields is high, do we need to downscale it?
df_all.to_sql("mode_power_distribution",pg_connection, schema="traffic",if_exists="replace", index_label="id")
with pg_connection.connect() as con:
    con.execute('ALTER TABLE traffic.mode_power_distribution ALTER "id" SET NOT NULL, ALTER "id" ADD GENERATED ALWAYS AS IDENTITY')
