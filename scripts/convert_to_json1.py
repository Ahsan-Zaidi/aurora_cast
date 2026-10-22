import boto3

BUCKET = 'aurora-cast-data-ahsan-v1'
PREFIX = 'raw/'

def main():
    s3 = boto3.client('s3')
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=BUCKET, Prefix=PREFIX)

    count = 0
    for page in pages:
        for obj in page.get("Contents", []):
            print(obj['Key'])
            count += 1
    print(f'Total: {count}')


if __name__ == '__main__':
    main()