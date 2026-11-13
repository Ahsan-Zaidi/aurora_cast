"""Score the persistence baseline: "the next block's Kp = this block's Kp."

The model must beat these scores to be useful. Persistence does well on
quiet days but is always one block late at the start and end of storms.

Validation results (2016-2019):
    MAE 0.618 | exactly right 20.29% | hit rate 41.62% | false alarm rate 58.59%

Usage: python model/baseline.py
"""

from split import load_splits
from metrics import score


def main():
    """Score persistence on the validation set and print the results."""
    train, valid, test = load_splits()

    # Persistence's forecast is simply this block's Kp
    results = score(valid['next_kp'], valid['kp'])

    print(f"Persistence MAE (valid): {results['mae']:.3f}")
    print(f"Exactly right (valid): {results['exact']:.2f}% of blocks.")
    print(f"Hit rate (valid): {results['hit_rate']:.2f}%")
    print(f"False alarm rate (valid): {results['false_alarm_rate']:.2f}%")


if __name__ == '__main__':
    main()