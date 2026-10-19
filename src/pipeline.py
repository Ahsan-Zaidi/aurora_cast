import requests
import sqlite3
import logging
import boto3
import json
from datetime import datetime, timezone

logging.basicConfig(
    filename='pipeline.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)

KP_URL = 'https://services.swpc.noaa.gov/json/planetary_k_index_1m.json'
WIND_URL = 'https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json'
MAG_URL = 'https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json'

# S3 bucket for raw NOAA data (us-east-1). The pipeline's IAM identity
# can only upload under raw/, so this is write-only by design.

S3_BUCKET = 'aurora-cast-data-ahsan-v1'

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
    in the mapping are left out. Records missing any mapped fields are
    skipped.

    Args:
        records: The list of records from extract_data.
        mapping: A dictionary pairing column names (keys) with
            NOAA field names (values).

    Returns:
        A list of tuples, one per complete record, in column order.
    """
    results = []
    for record in records:
        try:
            row = []
            for key in mapping.values():
                row.append(record[key])
        except KeyError:
            continue
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


def build_s3_key(feed_name, run_time):
    """Build the S3 key (file path) for one feed's raw data file.

    Keys follow the layout raw/feed=<feed>/date=<YYYY-MM-DD>/<HHMMSS>.json,
    so Athena can treat feed and date as partitions and read only the
    folders a query needs. The feed name is lowercased to keep paths
    consistent, since S3 keys are case-sensitive.

    Args:
        feed_name: The feed's name from FEEDS, such as 'Wind'.
        run_time: A UTC datetime for this pipeline run. Created once
        in main() so every feed from the same run shares one timestamp.

    Returns:
        The key as a string, like 'raw/feed=wind/date=2026-10-19/160316.json'.
    """
    feed = feed_name.lower()
    date_str = run_time.strftime('%Y-%m-%d')
    time_str = run_time.strftime('%H%M%S')
    key = f'raw/feed={feed}/date={date_str}/{time_str}.json'
    return key


def save_raw_to_s3(s3, bucket, key, records):
    """Upload one feed's records to S3 as a JSON file, exactly as received.

    Stores the raw NOAA data before any transformation, so the original
    can always be reprocessed later if the transform logic changes.

    Args:
        s3: A boto3 S3 client, created once in main().
        bucket: The name of the S3 bucket to upload to.
        key: The object's key, from build_s3_key.
        records: The list of records from extract_data.

    Raises:
        botocore.exceptions.ClientError: If the upload fails, for example
        because the credentials lack permission to write to the bucket.
    """
    json_text = json.dumps(records)
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json_text,
        ContentType='application/json',
    )


def main():
    """Run the pipeline once for every feed in FEEDS.

    Before the loop, open the SQLite connection, creates the S3 client,
    and records the run's start time in UTC. The same run time is used
    for every feed, so all files from one run share a timestamp.

    For each feed:
        1. Extract the records from NOAA.
        2. Save the raw records to S3, unchanged, under a key built
           from the feed name and run time.
        3. Transform the records into rows.
        4. Load the rows into the feed's SQLite table and commit.

    Each feed runs in its own try block, so if any step fails, the error
    is logged, that feed's pending database changes are rolled back, and
    the next feed still runs. An S3 upload failure also skips that
    feed's database load.

    Logs the start and end of every run, each S3 upload's key, how many
    records were fetched and added per feed, and warnings for skipped
    records, stale feeds (nothing new), and possible gaps (everything new).
    """
    con = sqlite3.connect('aurora_cast.db')
    run_time = datetime.now(timezone.utc)
    s3_client = boto3.client('s3')
    logging.info('Pipeline run started')


    for feed in FEEDS:
        try:
            records = extract_data(feed['url'])
            key = build_s3_key(feed['name'], run_time)
            save_raw_to_s3(s3_client, S3_BUCKET, key, records)
            logging.info(f'{feed["name"]} was saved - key: {key}')
            rows = transform_data(records, feed['mapping'])
            skipped = len(records) - len(rows)
            if skipped > 0:
                logging.warning(f'{feed["name"]} skipped {skipped} incomplete records')
            new = load_data(con, feed['table'], feed['mapping'].keys(), rows)
            con.commit()
            if new <= 0:
                logging.warning(f'{feed["name"]} returned no new data: {len(records)} fetched - {new} data added')
            elif new == len(rows):
                logging.warning(f'{feed["name"]}: possible gap in data {len(records)} fetched - {new} data added')
            else:
                logging.info(f'{feed["name"]} readings loaded: {len(records)} fetched - {new} added')
        except Exception:
            logging.exception(f'Failed to load {feed["name"]} records')
            con.rollback()
            

    logging.info('Pipeline run complete')
    con.close()


if __name__ == '__main__':
    main()