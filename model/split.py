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

train_storms = (train['next_kp'] >= 5).sum()
train_pct = train_storms / len(train) * 100

valid_storms = (valid['next_kp'] >= 5).sum()
valid_pct = valid_storms / len(valid) * 100

test_storms = (test['next_kp'] >= 5).sum()
test_pct = test_storms / len(test) * 100

print(f'train: {train_storms} storms ({train_pct:.1f}%)')
print(f'valid: {valid_storms} storms ({valid_pct:.1f}%)')
print(f'test: {test_storms} storms ({test_pct:.1f}%)')