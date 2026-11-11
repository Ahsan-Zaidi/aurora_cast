"""First look at the training table exported from Athena (training_blocks).

Checks size, column types, missing values, and that every year has the
expected number of 3-hour blocks (2,920, or 2,928 in leap years).

Usage: python model/explore.py   (expects data/training_blocks.csv)
"""

import pandas as pd

df = pd.read_csv('data/training_blocks.csv')

print(df.shape)
print(df.head())
print(df.dtypes)
print(df.isna().sum())

# CSV stores text only, so block_ts must be converted to a real timestamp
df['block_ts'] = pd.to_datetime(df['block_ts'])
print(df.dtypes)

print(df['block_ts'].dt.year.value_counts().sort_index())
