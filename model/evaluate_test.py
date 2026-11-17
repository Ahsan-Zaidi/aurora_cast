"""Final evaluation of Model v2 on the test set (2020-2026). Run once.

Every choice was locked in on validation before this runs: the v2 features,
the model settings, and the thresholds (4.33 main, 5 plain storm definition).
The model is retrained on train + valid (1995-2019) so it learns from the
most recent data before 2020, then scored once on test against persistence.

Do not change anything based on these results. That would turn the test set
into a second validation set, and the score would no longer be honest.

Usage: python model/evaluate_test.py
"""

import pandas as pd
from split import load_splits
from train import FEATURES, TARGET
from metrics import score
from sklearn.ensemble import HistGradientBoostingRegressor


def main():
    """Train v2 on 1995-2019, forecast 2020-2026, and print the final scores."""
    train, valid, test = load_splits('data/training_blocks_v2.csv')
    train_full = pd.concat([train, valid])

    x_train = train_full[FEATURES]
    y_train = train_full[TARGET]

    model = HistGradientBoostingRegressor(random_state=42)
    model.fit(x_train, y_train)

    predictions = model.predict(test[FEATURES])

    storms = (test[TARGET] >= 5).sum()
    print(f"Test set: {len(test)} blocks, {storms} storms\n")

    base_results = score(test[TARGET], test['kp'])
    print(f"{'Persistence':14} MAE {base_results['mae']:.3f} | "
          f"hit rate {base_results['hit_rate']:.2f}% | "
          f"false alarms {base_results['false_alarm_rate']:.2f}%")

    # Only the thresholds locked in on validation
    for threshold in [5, 4.33]:
        model_results = score(test[TARGET], predictions, threshold)
        print(f"{'Model >=' + str(threshold):14} MAE {model_results['mae']:.3f} | "
              f"hit rate {model_results['hit_rate']:.2f}% | "
              f"false alarms {model_results['false_alarm_rate']:.2f}%")


if __name__ == '__main__':
    main()