"""Load the GFZ Potsdam Kp archive into the AuroraCast data lake.

Downloads GFZ's three-hour Kp file (every block since 1932), converts each
line to a JSON record, and uploads all of it to S3 as one JSON Lines file:

    s3://aurora-cast-data-ahsan-v1/history/source=gfz_kp/kp_since_1932.jsonl

Each run REPLACES that file with GFZ's latest version, so the script is safe
to rerun (idempotent). Rerun it monthly: GFZ marks the current month as
preliminary (d_flag = 0) and finalizes it (d_flag = 1) after the month ends.

Usage (from the project folder, venv active):
    $env:AWS_PROFILE = "aurora-cast-dev"
    python scripts/load_gfz_kp.py

Permissions: s3:PutObject on history/* only (policy aurora-cast-history-write).
Queried in Athena as aurora_cast.gfz_kp (see sql/gfz_kp.sql).
"""

import requests
import json
import boto3


GFZ_URL = "https://kp.gfz.de/fileadmin/files_for_gfz_cms/Kp_ap_since_1932.txt"
S3_BUCKET = "aurora-cast-data-ahsan-v1"
KEY = "history/source=gfz_kp/kp_since_1932.jsonl"   # one file, replaced on every run


def extract_data(url):
    """Download a text file and return its contents as a string.

    Raises:
        requests.HTTPError: If the server returns an error status (e.g. 404).
    """
    response = requests.get(url, timeout=60)   # ~20 MB file, so allow extra time
    response.raise_for_status()                # stop on 404 / 500 instead of parsing an error page
    return response.text                       # .text is the body as a string (not JSON)


def parse_kp(text):
    """Turn GFZ's space-separated Kp file into a list of dicts.

    Each data line looks like:
        2026 10 10 15.0 16.50 34616.62500 34616.68750  7.333  154 0
        [0]  [1] [2] [3]  [4]     [5]         [6]       [7]   [8] [9]
    and becomes:
        {"block_start": "2026-10-10T15:00:00", "kp": 7.333, "ap": 154, "d_flag": 0}

    Args:
        text: The full contents of the GFZ file.

    Returns:
        A list of dicts, one per three-hour block. Missing values (GFZ's -1)
        are None, which becomes null in JSON and NULL in Athena.
    """
    results = []
    for line in text.splitlines():
        if line.startswith('#'):          # header lines explain the format; skip them
            continue
        parts = line.split()              # split on any run of spaces -> list of strings

        hour = int(float(parts[3]))       # '15.0' -> 15.0 -> 15 (block start hour, UTC)

        kp = float(parts[7])              # Kp in thirds: 7.333 = 7+, 8.667 = 9-
        if kp == -1:                      # GFZ's missing-value code
            kp = None

        ap = int(parts[8])                # the same activity on a linear scale
        if ap == -1:
            ap = None

        record = {
            # Same text format as NOAA's time_tag, so Athena can use the same date_parse
            'block_start': f'{parts[0]}-{parts[1]}-{parts[2]}T{hour:02d}:00:00',
            'kp': kp,
            'ap': ap,
            'd_flag': int(parts[9]),      # 1 = definitive, 0 = preliminary
        }
        results.append(record)
    return results


def save_to_s3(s3, bucket, key, records):
    """Upload records to S3 as JSON Lines (one JSON object per line).

    Args:
        s3: A boto3 S3 client.
        bucket: The bucket to upload to.
        key: The object's key; an existing file at this key is replaced.
        records: The list of dicts from parse_kp.
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
    """Download, parse and upload the GFZ Kp archive, then print a summary."""
    s3_client = boto3.client('s3')   # uses the credentials from $env:AWS_PROFILE

    text = extract_data(GFZ_URL)
    gfz_data = parse_kp(text)

    save_to_s3(s3_client, S3_BUCKET, KEY, gfz_data)
    print(f'Uploaded {len(gfz_data)} records to {KEY}')

    # Data quality summary: how many blocks had missing values?
    missing_kp = sum(1 for record in gfz_data if record['kp'] is None)
    print(f'Missing kp: {missing_kp}')
    missing_ap = sum(1 for record in gfz_data if record['ap'] is None)
    print(f'Missing ap: {missing_ap}')

    # The oldest and newest blocks: a quick check that the whole file was read
    print(gfz_data[0])
    print(gfz_data[-1])


if __name__ == '__main__':
    main()