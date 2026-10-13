import requests
import sqlite3

KP_URL = 'https://services.swpc.noaa.gov/json/planetary_k_index_1m.json'
WIND_URL = 'https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json'
MAG_URL = 'https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json'

KP_MAPPING = {
    'observed_at_utc': 'time_tag', 
    'estimated_kp': 'estimated_kp', 
    'kp_index': 'kp_index', 
    'kp': 'kp'
}

WIND_MAPPING = {
    'observed_at_utc': 'time_tag', 
    'source': 'source', 
    'active': 'active', 
    'proton_speed': 'proton_speed', 
    'proton_temp': 'proton_temperature', 
    'proton_density': 'proton_density', 
    'overall_quality': 'overall_quality'
}

MAG_MAPPING = {
    'observed_at_utc': 'time_tag', 
    'source': 'source', 
    'active': 'active', 
    'bt': 'bt', 
    'bz_gsm': 'bz_gsm', 
    'by_gsm': 'by_gsm', 
    'overall_quality': 'overall_quality'
}

def extract_data(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def transform_data(records, mapping):
    results = []
    for record in records:
        row = []
        for key in mapping.values():
            row.append(record[key])
        results.append(tuple(row))
    return results


def load_data(con, table, columns, rows):
    cur = con.cursor()
    joined = ', '.join(columns)
    values = ['?'] * len(columns)
    placeholder = ', '.join(values)
    sql = f'INSERT OR IGNORE INTO {table}({joined}) VALUES ({placeholder})'

    cur.executemany(sql, rows)


con = sqlite3.connect('aurora_cast.db')

kp_records = extract_data(KP_URL)
kp_rows = transform_data(kp_records, KP_MAPPING)
load_data(con, 'kp_readings', KP_MAPPING.keys(), kp_rows)

wind_records = extract_data(WIND_URL)
wind_rows = transform_data(wind_records, WIND_MAPPING)
load_data(con, 'rtsw_wind', WIND_MAPPING.keys(), wind_rows)

mag_records = extract_data(MAG_URL)
mag_rows = transform_data(mag_records, MAG_MAPPING)
load_data(con, 'rtsw_mag', MAG_MAPPING.keys(), mag_rows)

con.commit()
con.close()