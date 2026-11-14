from split import load_splits
from metrics import score
from sklearn.ensemble import HistGradientBoostingRegressor


FEATURES = ['kp', 'prev_kp', 'min_bz', 'max_bt', 'avg_speed', 'avg_density']
TARGET = 'next_kp'


def main():
    train, valid, test = load_splits()

    x_train = train[FEATURES]
    y_train = train[TARGET]

    model = HistGradientBoostingRegressor()
    model.fit(x_train, y_train)

    predictions = model.predict(valid[FEATURES])
    model_results = score(valid[TARGET], predictions)
    base_results = score(valid[TARGET], valid['kp'])

    for name, results in [('Persistence', base_results), ('Model', model_results)]:
        print(f"{name:12} MAE {results['mae']:.3f} | "
            f"exact {results['exact']:.2f}% | "
            f"hit rate {results['hit_rate']:.2f}% | "
            f"false alarms {results['false_alarm_rate']:.2f}%")


if __name__ == '__main__':
    main()
