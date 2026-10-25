import boto3
import json

BUCKET = 'aurora-cast-data-ahsan-v1'
PREFIX = 'raw/'


def main():
    s3 = boto3.client('s3')
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=BUCKET, Prefix=PREFIX)

    old_count = 0
    new_count = 0
    empty_count = 0
    mismatch_count = 0

    for page in pages:
        for obj in page.get("Contents", []):
            key = obj['Key']
            response = s3.get_object(Bucket=BUCKET, Key=key)
            text = response["Body"].read().decode('utf-8')

            if text.startswith('['):
                old_count += 1
                list_of_records = json.loads(text)
                new_text = "\n".join(json.dumps(record) for record in list_of_records)

                record_count = len(list_of_records)
                line_count = len(new_text.splitlines())

                if record_count == line_count:
                    print(f'{key}: {record_count} records, {line_count} lines, OK')
                else:
                    print(f'{key}: {record_count} records, {line_count} lines, MISMATCH')
                    mismatch_count += 1

            elif text.startswith('{'):
                new_count += 1
            else:
                empty_count += 1

    print(f'Old files to convert to JSON Lines: {old_count}')
    print(f'Already JSON Lines (skip): {new_count}')
    print(f'Empty files (skip): {empty_count}')
    print(f'Mismatches: {mismatch_count}')


if __name__ == '__main__':
    main()