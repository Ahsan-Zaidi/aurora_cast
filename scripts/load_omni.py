"""Load NASA OMNI2 hourly solar wind data (1995 to now) into the AuroraCast data lake.

For each year, downloads NASA's OMNI2 file (one line per hour, 55 numbers per
line), keeps the 6 measurements the model needs, converts NASA's fill values to
null, and uploads the year as one JSON Lines file:

    s3://aurora-cast-data-ahsan-v1/history/source=omni2/year=YYYY/omni2_YYYY.jsonl

Each run REPLACES each year's file, so the script is safe to rerun (idempotent).
Field names match the live views (wind_clean, mag_clean) so history and live
data line up.

Usage (from the project folder, venv active):
    $env:AWS_PROFILE = "aurora-cast-dev"
    python scripts/load_omni.py

Permissions: s3:PutObject on history/* only (policy aurora-cast-history-write).
Format reference: NASA OMNI2 hourly format (word numbers start at 1;
Python indexes start at 0, so index = word - 1).
"""

import requests
from datetime import datetime, timedelta
import boto3
import json


S3_BUCKET = "aurora-cast-data-ahsan-v1"
FIRST_YEAR = 1995   # solar wind coverage is much more complete from the mid-1990s on
LAST_YEAR = 2026    # inclusive; range() below adds 1 because its stop is excluded


def extract_data(url):
    """Download a text file and return its contents as a string.

    Raises:
        requests.HTTPError: If the server returns an error status (e.g. 404).
    """
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.text


def clean(value, fill):
    """Return None if value is NASA's fill code for this field, otherwise the value."""
    if value == fill:
        return None
    return value


def parse_omni(text):
    """Turn one year of OMNI2 hourly data into a list of dicts.

    Fields kept (NASA word -> Python index -> fill code):
        |B| average     word 9  -> [8]   999.9
        By GSM          word 16 -> [15]  999.9
        Bz GSM          word 17 -> [16]  999.9
        Temperature     word 23 -> [22]  9999999.
        Density         word 24 -> [23]  999.9
        Flow speed      word 25 -> [24]  9999.

    Args:
        text: The full contents of one omni2_YYYY.dat file.

    Returns:
        A list of dicts, one per hour, with fill values replaced by None.
    """
    result = []
    for line in text.splitlines():
        parts = line.split()                 # one line -> 55 pieces (as text)

        # Time: NASA gives year, DAY OF YEAR (Jan 1 = 1) and hour
        year = int(parts[0])
        day_of_year = int(parts[1])
        hour = int(parts[2])
        start_of_year = datetime(year, 1, 1)
        moment = start_of_year + timedelta(days=day_of_year - 1, hours=hour)
        hour_start = moment.isoformat()      # e.g. '2024-05-10T15:00:00'

        record = {
            'hour_start': hour_start,
            'bt': clean(float(parts[8]), 999.9),                           # nT
            'by_gsm': clean(float(parts[15]), 999.9),                      # nT
            'bz_gsm': clean(float(parts[16]), 999.9),                      # nT; negative = southward
            'proton_temperature': clean(float(parts[22]), 9999999.0),      # kelvin
            'proton_density': clean(float(parts[23]), 999.9),              # per cm^3
            'proton_speed': clean(float(parts[24]), 9999.0),               # km/s
        }
        result.append(record)

    return result


def save_to_s3(s3, bucket, key, records):
    """Upload records to S3 as JSON Lines (one JSON object per line).

    Args:
        s3: A boto3 S3 client.
        bucket: The bucket to upload to.
        key: The object's key; an existing file at this key is replaced.
        records: The list of dicts from parse_omni.
    """
    json_lines = []
    for record in records:
        json_lines.append(json.dumps(record))   # one dict -> one JSON string
    result = "\n".join(json_lines)              # one record per line, for Athena
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=result,
        ContentType='application/x-ndjson',
    )


def main():
    """Download, parse and upload every OMNI2 year, printing one summary line per year."""
    s3_client = boto3.client('s3')   # created once, reused for every year

    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        url = f'https://cdaweb.gsfc.nasa.gov/pub/data/omni/low_res_omni/omni2_{year}.dat'
        key = f'history/source=omni2/year={year}/omni2_{year}.jsonl'

        try:
            text = extract_data(url)
        except requests.HTTPError as error:
            # e.g. the current year's file isn't published yet: skip it, keep going
            print(f'{year}: skipped ({error})')
            continue

        omni_data = parse_omni(text)
        save_to_s3(s3_client, S3_BUCKET, key, omni_data)

        missing_bt = sum(1 for record in omni_data if record['bt'] is None)
        missing_speed = sum(1 for record in omni_data if record['proton_speed'] is None)
        print(f'{year}: {len(omni_data)} hours, missing bt {missing_bt}, '
              f'missing speed {missing_speed} -> {key}')


if __name__ == '__main__':
    main()