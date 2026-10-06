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

con.commit()
con.close()