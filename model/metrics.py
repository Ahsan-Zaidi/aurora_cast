"""Scores shared by every forecast (baseline and model), so all are judged the same way.

    mae               average distance from the truth, in Kp units
    exact             % of blocks predicted exactly right
    hit_rate          % of real storms (Kp >= 5) that were predicted
    false_alarm_rate  % of predicted storms that did not happen

Storms are rare (~2-3% of blocks), so MAE alone can look good while
missing every storm; the two storm scores catch that.
"""


def score(truth, forecast):
    """Score a forecast against the truth.

    Args:
        truth: The actual Kp of each block (e.g. valid['next_kp']).
        forecast: The predicted Kp of each block, same rows and order.

    Returns:
        A dict with mae, exact, hit_rate and false_alarm_rate.
        false_alarm_rate is nan if the forecast never predicts a storm.
    """
    error = (truth - forecast).abs()
    mae = error.mean()

    exact = (forecast == truth).mean() * 100

    actual_storm = truth >= 5
    predicted_storm = forecast >= 5

    # Compare the True/False columns row by row first, then count with .sum()
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