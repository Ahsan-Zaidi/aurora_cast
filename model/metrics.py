def score(truth, forecast):
    error = (truth - forecast).abs()
    mae = error.mean()

    exact = (forecast == truth).mean() * 100

    actual_storm = truth >= 5
    predicted_storm = forecast >= 5

    hits = (actual_storm & predicted_storm).sum()
    false_alarms = (predicted_storm & ~actual_storm).sum()

    hit_rate = (hits / actual_storm.sum()) * 100
    false_alarm_rate = (false_alarms / predicted_storm.sum()) * 100

    return {
        'mae': mae,
        'exact': exact,
        'hit_rate': hit_rate,
        'false_alarm_rate': false_alarm_rate,
    }