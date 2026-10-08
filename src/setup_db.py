import sqlite3

con = sqlite3.connect('aurora_cast.db')
cur = con.cursor()

cur.execute(
    '''CREATE TABLE IF NOT EXISTS kp_readings(
        observed_at_utc TEXT PRIMARY KEY NOT NULL, 
        estimated_kp REAL NOT NULL, 
        kp_index INTEGER, 
        kp TEXT
    )'''
)

cur.execute(
    '''CREATE TABLE IF NOT EXISTS rtsw_wind(
        observed_at_utc TEXT NOT NULL,
        source TEXT NOT NULL,
        active INTEGER,
        proton_speed REAL,
        proton_temp REAL,
        proton_density REAL,
        overall_quality INTEGER,
        PRIMARY KEY (observed_at_utc, source)
    )'''
)

cur.execute(
    '''CREATE TABLE IF NOT EXISTS rtsw_mag(
        observed_at_utc TEXT NOT NULL,
        source TEXT NOT NULL,
        active INTEGER,
        bt REAL,
        bz_gsm REAL,
        by_gsm REAL,
        overall_quality INTEGER,
        PRIMARY KEY (observed_at_utc, source)
    )'''
)

con.commit()
con.close()