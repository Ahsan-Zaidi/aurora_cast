"""Split the training table by time into train, validation and test sets.

    train  1995-2015   the model learns from these
    valid  2016-2019   used to check and adjust the model
    test   2020-2026   used once, at the end, for the final score

Split by time, never randomly: neighboring blocks are nearly identical,
so a random split would leak test answers into training.

Usage: python model/split.py
"""
import pandas as pd


def load_splits():
    """Load training_blocks.csv and return (train, valid, test), split by year."""

    df = pd.read_csv('data/training_blocks.csv')
    df['block_ts'] = pd.to_datetime(df['block_ts'])

    year = df['block_ts'].dt.year

    train = df[(year >= 1995) & (year <= 2015)]
    valid = df[(year >= 2016) & (year <= 2019)]
    test = df[(year >= 2020) & (year <= 2026)]

    return train, valid, test


def main():
    train, valid, test = load_splits()
    # The three sizes must add up to the full table (no row lost or doubled)
    print(f'train: {len(train)}')
    print(f'valid: {len(valid)}')
    print(f'test:  {len(test)}')
    print(f'total: {len(train) + len(valid) + len(test)}')

    for name, part in [('train', train), ('valid', valid), ('test', test)]:
        storms = (part['next_kp'] >= 5).sum()
        pct = storms / len(part) * 100
        print(f'{name}: {storms} storms ({pct:.1f}%)')


if __name__ == '__main__':
    main()