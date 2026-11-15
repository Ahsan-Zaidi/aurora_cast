"""Train the gradient boosting model and compare it with persistence on validation.

The model learns from train (1995-2015) and forecasts valid (2016-2019),
which it has never seen. Its storm scores are shown at several thresholds:
the forecasts stay the same, only how they are read as "storm" changes.

Usage: python model/train.py
"""

from split import load_splits
from metrics import score
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance


FEATURES = ['kp', 'prev_kp', 'min_bz', 'max_bt', 'avg_speed', 'avg_density']
TARGET = 'next_kp'



def main():
    """Train on train, forecast valid, and print persistence vs model scores."""
    train, valid, test = load_splits()

    x_train = train[FEATURES]
    y_train = train[TARGET]

    model = HistGradientBoostingRegressor(random_state=42)
    model.fit(x_train, y_train)

    predictions = model.predict(valid[FEATURES])

    base_results = score(valid[TARGET], valid['kp'])
    print(f"{'Persistence':14} MAE {base_results['mae']:.3f} | "
          f"hit rate {base_results['hit_rate']:.2f}% | "
          f"false alarms {base_results['false_alarm_rate']:.2f}%")

    # Same predictions, read as "storm" at different thresholds (no retraining)
    for threshold in [5, 4.4, 4.33, 4.25, 4.2]:
        model_results = score(valid[TARGET], predictions, threshold)
        print(f"{'Model >=' + str(threshold):14} MAE {model_results['mae']:.3f} | "
              f"hit rate {model_results['hit_rate']:.2f}% | "
              f"false alarms {model_results['false_alarm_rate']:.2f}%")

    # Permutation importance: shuffle one feature at a time on valid
    # and measure how much MAE gets worse (bigger = model relies on it more)
    r = permutation_importance(model, valid[FEATURES], valid[TARGET],
                               n_repeats=10, random_state=42,
                               scoring="neg_mean_absolute_error")

    print("\nFeature importance (MAE increase when shuffled):")
    pairs = zip(FEATURES, r.importances_mean)
    for name, s in sorted(pairs, key=lambda p: p[1], reverse=True):
        print(f"{name:14} {s:.3f}")


if __name__ == '__main__':
    main()