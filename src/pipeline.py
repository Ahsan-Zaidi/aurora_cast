import requests
import logging
import boto3
import json
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)
logging.getLogger().setLevel(logging.INFO)

KP_URL = 'https://services.swpc.noaa.gov/json/planetary_k_index_1m.json'
WIND_URL = 'https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json'
MAG_URL = 'https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json'

# S3 bucket for raw NOAA data (us-east-1). The pipeline's IAM identity
# can only upload under raw/, so this is write-only by design.

S3_BUCKET = 'aurora-cast-data-ahsan-v1'

# Each feed the pipeline loads
# Add a new dictionary here to bring in a new data source

FEEDS = [
    {
        'name': 'Kp',
        'url': KP_URL,
    },
    {
        'name': 'Wind',
        'url': WIND_URL,
    },
    {
        'name': 'Mag',
        'url': MAG_URL,
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

    Before the loop, records the run's start time in UTC and creates the
    S3 client. The same run time is used for every feed, so all files
    from one run share a timestamp.

    For each feed:
        1. Extract the records from NOAA.
        2. Save the raw records to S3, unchanged, under a key built
           from the feed name and run time.

    Each feed runs in its own try block, so if fetching or saving fails,
    the error is logged with its traceback and the next feed still runs.

    Logs the start and end of every run, and for each feed, how many
    records were saved and the S3 key they were saved under.
    """
    run_time = datetime.now(timezone.utc)
    s3_client = boto3.client('s3')
    logging.info('Pipeline run started')


    for feed in FEEDS:
        try:
            records = extract_data(feed['url'])
            key = build_s3_key(feed['name'], run_time)
            save_raw_to_s3(s3_client, S3_BUCKET, key, records)
            logging.info(f'{feed["name"]}: saved {len(records)} to {key}')
        except Exception:
            logging.exception(f'Failed to save {feed["name"]} records')
            

    logging.info('Pipeline run complete')


def lambda_handler(event, context):
    """Entry point that AWS Lambda calls on each scheduled run.

    Runs the pipeline once by calling main(). Lambda always passes
    these two arguments, even though the pipeline doesn't use them.

    Args:
        event: Details about what triggered the run (the EventBridge
            schedule).
        context: Information about this Lambda invocation, such as the
            time remaining before it times out.
    """
    main()


if __name__ == '__main__':
    main()