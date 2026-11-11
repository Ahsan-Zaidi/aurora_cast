import pandas as pd

df = pd.read_csv('data/training_blocks.csv')
df['block_ts'] = pd.to_datetime(df['block_ts'])

year = df['block_ts'].dt.year

train = df[(year >= 1995) & (year <= 2015)]
valid = df[(year >= 2016) & (year <= 2019)]
test = df[(year >= 2020) & (year <= 2026)]

print(f'train: {len(train)}')
print(f'valid: {len(valid)}')
print(f'test:  {len(test)}')
print(f'total: {len(train) + len(valid) + len(test)}')