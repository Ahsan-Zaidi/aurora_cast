"""One-time backfill: convert old raw files in S3 from JSON arrays to JSON Lines.

Before Oct 21, 2026, save_raw_to_s3 wrote each feed as one JSON array on a
single line. Athena reads one JSON object per line, so those files could not
be queried. This script finds every old-format file under raw/, converts it
to JSON Lines, checks that no records were lost, and writes it back under the
same key.

Safe to rerun (idempotent): files that already start with "{" are skipped.

Usage (in AWS CloudShell, as an identity with s3:ListBucket, GetObject and
PutObject on the bucket; NOT the aurora-cast-dev user, which can only write):
    1. Run with DRY_RUN = True and check that Mismatches is 0.
    2. Set DRY_RUN = False and run again to write the converted files.
    3. Run once more: "Old files to convert" should be 0.

Back up raw/ before step 2; the bucket has no versioning.
"""

import boto3
import json

BUCKET = 'aurora-cast-data-ahsan-v1'
PREFIX = 'raw/'     # only files under raw/ are checked
DRY_RUN = True      # True = report only, write nothing. False = overwrite old files.


def main():
    """List every file under PREFIX, convert old-format ones, and print a summary."""
    s3 = boto3.client('s3')

    # S3 returns at most 1,000 keys per request; the paginator fetches every page.
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=BUCKET, Prefix=PREFIX)

    # Counters start once, before the loops, and add up across every page.
    old_count = 0       # JSON array files ("[") that need converting
    new_count = 0       # files already in JSON Lines ("{")
    empty_count = 0     # files with no content
    mismatch_count = 0  # conversions that failed the record/line check

    for page in pages:
        # "Contents" is missing when a page has no files, so default to [].
        for obj in page.get("Contents", []):
            key = obj['Key']  # the file's full name, e.g. raw/feed=kp/date=2026-10-19/180211.json

            # Listing gives names only; read this file's contents separately.
            response = s3.get_object(Bucket=BUCKET, Key=key)
            text = response["Body"].read().decode('utf-8')  # stream -> bytes -> string

            if text.startswith('['):
                # Old format: one JSON array on one line.
                old_count += 1

                # Convert in memory: array text -> list of dicts -> one JSON object per line.
                list_of_records = json.loads(text)
                new_text = "\n".join(json.dumps(record) for record in list_of_records)

                # Safety check: every record must become exactly one line.
                record_count = len(list_of_records)
                line_count = len(new_text.splitlines())

                if record_count == line_count:
                    if not DRY_RUN:
                        # Overwrite the original under the same key.
                        s3.put_object(
                            Bucket=BUCKET,
                            Key=key,
                            Body=new_text,
                            ContentType='application/x-ndjson',
                        )
                        # Printed only after put_object succeeds.
                        print(f'{key}: {record_count} records, {line_count} lines, CONVERTED')
                    else:
                        print(f'{key}: {record_count} records, {line_count} lines, OK (dry run)')
                else:
                    # Never overwrite a file whose conversion looks wrong; leave it for review.
                    print(f'{key}: {record_count} records, {line_count} lines, MISMATCH')
                    mismatch_count += 1

            elif text.startswith('{'):
                # Already JSON Lines (written by the pipeline after Oct 21): skip.
                new_count += 1
            else:
                # Empty file: nothing to convert.
                empty_count += 1

    # Summary, printed once after every file has been checked.
    print(f'Old files to convert to JSON Lines: {old_count}')
    print(f'Already JSON Lines (skip): {new_count}')
    print(f'Empty files (skip): {empty_count}')
    print(f'Mismatches: {mismatch_count}')


if __name__ == '__main__':
    main()