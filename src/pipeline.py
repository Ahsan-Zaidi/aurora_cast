import requests
import sqlite3

KP_URL = 'https://services.swpc.noaa.gov/json/planetary_k_index_1m.json'
WIND_URL = 'https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json'
MAG_URL = 'https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json'


# Each mapping connects the database column (key) to the NOAA field it's pulled from (value)
# The order of the mapping matters: transform_data and load_data both rely on it lining up

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
    """Download a NOAA JSON feed and return its records.

    Args:
        url: The web address of the NOAA feed.

    Returns:
        A list of records, where each record is a dictionary.

    Raises:
        requests.HTTPError: If NOAA sends back an error status.
    """
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def transform_data(records, mapping):
    """Turn NOAA records into rows ready for the database.

    For each record, pulls out only the fields listed in the mapping,
    in the mapping's order, and packs them into a tuple. Fields not
    in the mapping are left out.

    Args:
        records: The list of records from extract_data.
        mapping: A dictionary pairing column names (keys) with
            NOAA field names (values).

    Returns:
        A list of tuples, one per record, in column order.
    """
    results = []
    for record in records:
        row = []
        for key in mapping.values():
            row.append(record[key])
        results.append(tuple(row))
    return results


def load_data(con, table, columns, rows):
    """Insert rows into a database table, skipping duplicates.

    Builds the INSERT statement from the table and column names,
    then inserts every row at once. Rows that already exist
    (same primary key) are ignored.

    Does not commit. The caller must call con.commit() afterward,
    or the rows will not be saved.

    Args:
        con: An open SQLite connection.
        table: The name of the table to insert into.
        columns: The column names, in the same order as the values
            in each row (usually mapping.keys()).
        rows: The list of tuples from transform_data.
    """
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
con.commit()

wind_records = extract_data(WIND_URL)
wind_rows = transform_data(wind_records, WIND_MAPPING)
load_data(con, 'rtsw_wind', WIND_MAPPING.keys(), wind_rows)
con.commit()

mag_records = extract_data(MAG_URL)
mag_rows = transform_data(mag_records, MAG_MAPPING)
load_data(con, 'rtsw_mag', MAG_MAPPING.keys(), mag_rows)
con.commit()

con.close()