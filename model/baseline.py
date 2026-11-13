from split import load_splits
from metrics import score


def main():
    train, valid, test = load_splits()
    results = score(valid['next_kp'], valid['kp'])

    print(f"Persistence MAE (valid): {results['mae']:.3f}")
    print(f"Exactly right (valid): {results['exact']:.2f}% of blocks.")
    print(f"Hit rate (valid): {results['hit_rate']:.2f}%")
    print(f"False alarm rate (valid): {results['false_alarm_rate']:.2f}%")


if __name__ == '__main__':
    main()