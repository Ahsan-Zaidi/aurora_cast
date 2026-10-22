import boto3

BUCKET = 'aurora-cast-data-ahsan-v1'
PREFIX = 'raw/'

def main():
    s3 = boto3.client('s3')
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=BUCKET, Prefix=PREFIX)

    old_count = 0
    new_count = 0
    empty_count = 0
    for page in pages:
        for obj in page.get("Contents", []):
            key = obj['Key']
            response = s3.get_object(Bucket=BUCKET, Key=key)
            text = response["Body"].read().decode('utf-8')
            if text.startswith('['):
                old_count += 1
                print(key)
            elif text.startswith('{'):
                new_count += 1
            else:
                empty_count += 1
    print(f'Old files that need to convert to JSON lines: {old_count}')
    print(f'Already JSON lines: {new_count}')
    print(f'Empty files (skip): {empty_count}')


if __name__ == '__main__':
    main()