from config.credentials import Config
import psycopg2

# Private config object for module wide use
cfg = Config()
cfg.user_credentials('database')

def create_table():
    
    try:
        conn = psycopg2.connect(cfg.postgresql_string())
    except: 
        raise Exception("Couldn't connect to database")
    cursor = conn.cursor()

    # Drop possible existing table before creating a new one
    try:
        cursor.execute("DROP TABLE IF EXISTS energy_modes")
    except:
        raise RuntimeError("Couldn't drop existing table")

    # Create new table energy modes
    try:
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
    except:
        raise RuntimeError("Couldn't create the table")

    # commit changes and close connection
    conn.commit()
    cursor.close()
    conn.close()

def insert_passenger_cars(mun_code:str, cars_dict:dict):
    try:
        conn = psycopg2.connect(cfg.postgresql_string())
    except: 
        raise Exception("Couldn't connect to database")
    cursor = conn.cursor()

    # insert passenger cars to table
    insert_into = ("""INSERT INTO energy_modes(mun, scenario, year, kmuoto , kvoima_bensiini, kvoima_diesel, kvoima_etanoli, kvoima_kaasu, kvoima_phev_b, kvoima_phev_d, 
              kvoima_ev, kvoima_vety, kvoima_muut) 
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""")
    try:
        cursor.execute(insert_into, (mun_code, 'wem', 2021, 'hlauto', cars_dict["kvoima_bensiini"], cars_dict["kvoima_diesel"], cars_dict["kvoima_etanoli"], 
                cars_dict["kvoima_kaasu"], cars_dict["kvoima_phev_b"], cars_dict["kvoima_phev_d"], cars_dict["kvoima_ev"],
                cars_dict["kvoima_vety"], cars_dict["kvoima_muut"]))
    except:
        raise RuntimeError("Couldn't insert into table")

    # commit and close
    conn.commit()
    cursor.close()
    conn.close()

def insert_walking_biking(mun_code:str):
    try:
        conn = psycopg2.connect(cfg.postgresql_string())
    except: 
        raise Exception("Couldn't connect to database")
    cursor = conn.cursor()
    
    insert_into = ("""INSERT INTO energy_modes(mun, scenario, year, kmuoto , kvoima_bensiini, kvoima_diesel, kvoima_etanoli, kvoima_kaasu, kvoima_phev_b, kvoima_phev_d, 
              kvoima_ev, kvoima_vety, kvoima_muut) 
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""")
    cursor.execute(insert_into, (mun_code, 'wem', 2021,'jalkapyora', 0, 0, 0, 0, 0, 0, 0, 0, 0))

    # commit and close
    conn.commit()
    cursor.close()
    conn.close()

def insert_rail(mun_code:str):
    try:
        conn = psycopg2.connect(cfg.postgresql_string())
    except: 
        raise Exception("Couldn't connect to database")
    cursor = conn.cursor()

    insert_into = ("""INSERT INTO energy_modes(mun, scenario, year, kmuoto , kvoima_bensiini, kvoima_diesel, kvoima_etanoli, kvoima_kaasu, kvoima_phev_b, kvoima_phev_d, 
              kvoima_ev, kvoima_vety, kvoima_muut) 
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""")
    cursor.execute(insert_into, (mun_code, 'wem', 2021,'raide', 0, 0, 0, 0, 0, 0, 1, 0, 0))

    # commit and close
    conn.commit()
    cursor.close()
    conn.close()

def insert_vans(mun_code:str, vans_dict:dict):
    try:
        conn = psycopg2.connect(cfg.postgresql_string())
    except: 
        raise Exception("Couldn't connect to database")
    cursor = conn.cursor()

    insert_into = ("""INSERT INTO energy_modes(mun, scenario, year, kmuoto , kvoima_bensiini, kvoima_diesel, kvoima_etanoli, kvoima_kaasu, kvoima_phev_b, kvoima_phev_d, 
              kvoima_ev, kvoima_vety, kvoima_muut) 
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""")
    cursor.execute(insert_into, (mun_code, 'wem', 2021, 'pauto', vans_dict["kvoima_bensiini"], vans_dict["kvoima_diesel"], vans_dict["kvoima_etanoli"], 
              vans_dict["kvoima_kaasu"], vans_dict["kvoima_phev_b"], vans_dict["kvoima_phev_d"], vans_dict["kvoima_ev"],
              vans_dict["kvoima_vety"], vans_dict["kvoima_muut"]))

    # commit and close
    conn.commit()
    cursor.close()
    conn.close()

def insert_trucks(mun_code:str, trucks_dict:dict):
    try:
        conn = psycopg2.connect(cfg.postgresql_string())
    except: 
        raise Exception("Couldn't connect to database")
    cursor = conn.cursor()

    insert_into = ("""INSERT INTO energy_modes(mun, scenario, year, kmuoto , kvoima_bensiini, kvoima_diesel, kvoima_etanoli, kvoima_kaasu, kvoima_phev_b, kvoima_phev_d, 
              kvoima_ev, kvoima_vety, kvoima_muut) 
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""")
    cursor.execute(insert_into, (mun_code, 'wem', 2021, 'kauto', trucks_dict["kvoima_bensiini"], trucks_dict["kvoima_diesel"], trucks_dict["kvoima_etanoli"], 
              trucks_dict["kvoima_kaasu"], trucks_dict["kvoima_phev_b"], trucks_dict["kvoima_phev_d"], trucks_dict["kvoima_ev"],
              trucks_dict["kvoima_vety"], trucks_dict["kvoima_muut"]))

    # commit and close
    conn.commit()
    cursor.close()
    conn.close()

def insert_busses(mun_code:str, busses_dict:dict):
    try:
        conn = psycopg2.connect(cfg.postgresql_string())
    except: 
        raise Exception("Couldn't connect to database")
    cursor = conn.cursor()

    insert_into = ("""INSERT INTO energy_modes(mun, scenario, year, kmuoto , kvoima_bensiini, kvoima_diesel, kvoima_etanoli, kvoima_kaasu, kvoima_phev_b, kvoima_phev_d, 
              kvoima_ev, kvoima_vety, kvoima_muut) 
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""")
    cursor.execute(insert_into, (mun_code, 'wem', 2021, 'bussi', busses_dict["kvoima_bensiini"], busses_dict["kvoima_diesel"], busses_dict["kvoima_etanoli"], 
              busses_dict["kvoima_kaasu"], busses_dict["kvoima_phev_b"], busses_dict["kvoima_phev_d"], busses_dict["kvoima_ev"],
              busses_dict["kvoima_vety"], busses_dict["kvoima_muut"]))

    # commit and close
    conn.commit()
    cursor.close()
    conn.close()

def insert_others(mun_code:str):
    try:
        conn = psycopg2.connect(cfg.postgresql_string())
    except: 
        raise Exception("Couldn't connect to database")
    cursor = conn.cursor()

    insert_into = ("""INSERT INTO energy_modes(mun, scenario, year, kmuoto , kvoima_bensiini, kvoima_diesel, kvoima_etanoli, kvoima_kaasu, kvoima_phev_b, kvoima_phev_d, 
              kvoima_ev, kvoima_vety, kvoima_muut) 
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""")
    cursor.execute(insert_into, (mun_code, 'wem', 2021,'muu', 0, 0, 0, 0, 0, 0, 0, 0, 1))

    # commit and close
    conn.commit()
    cursor.close()
    conn.close()
