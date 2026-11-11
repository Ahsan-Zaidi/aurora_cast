import pandas as pd

df = pd.read_csv('data/training_blocks.csv')
df['block_ts'] = pd.to_datetime(df['block_ts'])
print(df.dtypes)
print(df['block_ts'].dt.year.head())
print(df['block_ts'].dt.year.value_counts().sort_index())
