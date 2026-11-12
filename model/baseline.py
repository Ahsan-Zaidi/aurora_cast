from split import load_splits


def main():
    train, valid, test = load_splits()

    forecast = valid['kp']
    error = (valid['next_kp'] - forecast).abs()
    mae = error.mean()

    print(f'Persistence MAE (valid): {mae:.3f}')

    exact = (forecast == valid['next_kp']).mean() * 100
    print(f'Exactly right: {exact:.1f}% of blocks')

    actual_storm = valid['next_kp'] >= 5
    predicted_storm = valid['kp'] >= 5

    hits = (actual_storm & predicted_storm).sum()
    false_alarms = (predicted_storm & ~actual_storm).sum()

    hit_rate = (hits / actual_storm.sum()) * 100
    false_alarm_rate = (false_alarms / predicted_storm.sum()) * 100

    print(f'Real storms: {actual_storm.sum()} | Hits: {hits} | Hit rate: {hit_rate:.1f}% | False alarm rate: {false_alarm_rate:.1f}%')




if __name__ == '__main__':
    main()