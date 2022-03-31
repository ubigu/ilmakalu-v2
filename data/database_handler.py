from config.credentials import Config
import psycopg2

# Private config object for module wide use
cfg = Config()
cfg.user_credentials('database')

def create_table():
    
    # try to connect to database
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

def insert_data(mun_code:str, transport_type:str, data:dict=None):
    
    # check that a call with passenger car, van, truck or bus was supplied with data
    if transport_type in ("passenger car", "van", "truck", "bus") and data == None:
        raise ValueError("The transport type specified by you requires data input")
    
    # connect to database
    try:
        conn = psycopg2.connect(cfg.postgresql_string())
    except: 
        raise Exception("Couldn't connect to database")
    cursor = conn.cursor()

    # insert into -argument
    insert_into = ("""INSERT INTO energy_modes(mun, scenario, year, kmuoto , kvoima_bensiini, kvoima_diesel, kvoima_etanoli, kvoima_kaasu, kvoima_phev_b, kvoima_phev_d, 
    kvoima_ev, kvoima_vety, kvoima_muut) 
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""")

    # add data to database according to transport type
    try:
        # passenger cars
        if transport_type == "passenger car":
            cursor.execute(insert_into, (mun_code, 'wem', 2021, 'hlauto', data["kvoima_bensiini"], data["kvoima_diesel"], data["kvoima_etanoli"], 
                    data["kvoima_kaasu"], data["kvoima_phev_b"], data["kvoima_phev_d"], data["kvoima_ev"],
                    data["kvoima_vety"], data["kvoima_muut"]))

        # vans
        elif transport_type == "van":
            cursor.execute(insert_into, (mun_code, 'wem', 2021, 'pauto', data["kvoima_bensiini"], data["kvoima_diesel"], data["kvoima_etanoli"], 
                data["kvoima_kaasu"], data["kvoima_phev_b"], data["kvoima_phev_d"], data["kvoima_ev"],
                data["kvoima_vety"], data["kvoima_muut"]))
        
        # trucks
        elif transport_type == "truck":
            cursor.execute(insert_into, (mun_code, 'wem', 2021, 'kauto', data["kvoima_bensiini"], data["kvoima_diesel"], data["kvoima_etanoli"], 
                    data["kvoima_kaasu"], data["kvoima_phev_b"], data["kvoima_phev_d"], data["kvoima_ev"],
                    data["kvoima_vety"], data["kvoima_muut"]))

        # busses
        elif transport_type == "bus":
            cursor.execute(insert_into, (mun_code, 'wem', 2021, 'bussi', data["kvoima_bensiini"], data["kvoima_diesel"], data["kvoima_etanoli"], 
                data["kvoima_kaasu"], data["kvoima_phev_b"], data["kvoima_phev_d"], data["kvoima_ev"],
                data["kvoima_vety"], data["kvoima_muut"]))
        
        # rail
        elif transport_type == "rail":
            cursor.execute(insert_into, (mun_code, 'wem', 2021,'raide', 0, 0, 0, 0, 0, 0, 1, 0, 0))

        # walking and biking
        elif transport_type == "walking/biking":
            cursor.execute(insert_into, (mun_code, 'wem', 2021,'jalkapyora', 0, 0, 0, 0, 0, 0, 0, 0, 0))

        # others
        elif transport_type == "other":
            cursor.execute(insert_into, (mun_code, 'wem', 2021,'muu', 0, 0, 0, 0, 0, 0, 0, 0, 1))

        # Let user know that the chosen transport type wasn't among allowed alternatives
        else:
            raise ValueError("Transport type must be one of the following: passenger car, van, truck, bus, rail, walking/biking, other")
                
    except:
        raise RuntimeError(f"Couldn't insert {transport_type} data into the table")

    # commit changes and close database connection
    conn.commit()
    cursor.close()
    conn.close()