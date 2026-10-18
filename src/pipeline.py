import requests
import sqlite3
import logging

logging.basicConfig(
    filename='pipeline.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)

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

# Each feed the pipeline loads
# Add a new dictionary here to bring in a new data source

FEEDS = [
    {
        'name': 'Kp',
        'url': KP_URL,
        'table': 'kp_readings',
        'mapping': KP_MAPPING,
    },
    {
        'name': 'Wind',
        'url': WIND_URL,
        'table': 'rtsw_wind',
        'mapping': WIND_MAPPING,
    },
    {
        'name': 'Mag',
        'url': MAG_URL,
        'table': 'rtsw_mag',
        'mapping': MAG_MAPPING,
    },
]


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

    Returns:
        The number of new rows inserted (duplicate rows are not counted)
    """
    cur = con.cursor()
    joined = ', '.join(columns)
    values = ['?'] * len(columns)
    placeholder = ', '.join(values)
    sql = f'INSERT OR IGNORE INTO {table}({joined}) VALUES ({placeholder})'

    cur.executemany(sql, rows)
    return cur.rowcount


con = sqlite3.connect('aurora_cast.db')
logging.info('Pipeline run started')


for feed in FEEDS:
    try:
        records = extract_data(feed['url'])
        rows = transform_data(records, feed['mapping'])
        new = load_data(con, feed['table'], feed['mapping'].keys(), rows)
        con.commit()
        if new <= 0:
            logging.warning(f'{feed["name"]} returned no new data: {len(records)} fetched - {new} data added')
        elif new == len(records):
            logging.warning(f'{feed["name"]}: possible gap in data {len(records)} fetched - {new} data added')
        else:
            logging.info(f'{feed["name"]} readings loaded: {len(records)} fetched - {new} added')
    except Exception:
        logging.exception(f'Failed to load {feed["name"]} records')
        con.rollback()
        

logging.info('Pipeline run complete')
con.close()