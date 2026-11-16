# AuroraCast: Experiments Log

Everything is compared against **Model v1** on the validation set (2016-2019, 197 storms).

| | MAE | Hit rate | False alarms |
|---|---|---|---|
| Persistence | 0.618 | 41.62% | 58.59% |
| v1 @ ≥5 | 0.547 | 21.32% | 32.26% |
| v1 @ ≥4.33 | 0.547 | 49.75% | 54.84% |

Valid only has 197 storms, so 1 storm is about 0.5% of hit rate. Changes of a few percent are basically noise.

---

## Experiment 1: Southward Bz x speed
**Date:** 2026-11-15
**Result:** Rejected, went back to v1

**Change:** Added two features:
- `south_bz = (-min_bz).clip(lower=0)` (keeps only southward Bz, northward becomes 0)
- `speed_x_south_bz = south_bz * avg_speed`

**Idea:** Storms happen when fast solar wind comes with strong southward Bz, so I thought giving the model that product directly would help.

| | MAE | Hit rate | False alarms |
|---|---|---|---|
| v1 @ ≥5 | 0.547 | 21.32% | 32.26% |
| Exp 1 @ ≥5 | 0.547 | 21.83% | 29.51% |
| v1 @ ≥4.33 | 0.547 | 49.75% | 54.84% |
| Exp 1 @ ≥4.33 | 0.547 | 47.72% | 55.24% |

**What happened:** MAE didn't move, and the storm numbers shifted by a few storms in both directions. Trees can already combine `min_bz` and `avg_speed` by splitting on one and then the other, so the new feature didn't give the model anything it couldn't already figure out. Kept the simpler model.

**Takeaway:** Hand-made interaction features matter more for linear models than for trees.

---

## Feature importance check (v1)
**Date:** 2026-11-15

Not an experiment, just looking at what v1 relies on. I used permutation importance on valid: shuffle one column, see how much worse MAE gets.

| Feature | MAE increase |
|---|---|
| kp | 0.284 |
| avg_speed | 0.174 |
| min_bz | 0.061 |
| max_bt | 0.048 |
| avg_density | 0.041 |
| prev_kp | 0.003 |

`prev_kp` does almost nothing. It's mostly the same information as `kp`, and `kp` is more recent. That probably means adding more past data (like the previous block's solar wind) won't help much either.

The bigger issue: v1's hit rate more than doubles going from ≥5 to ≥4.33. So for a lot of real storms the model forecasts something like 4.3-5. It sees them coming but undershoots. Storm weighting seemed like the fix for that.

---

## Experiment 2: Storm weighting
**Date:** 2026-11-15
**Result:** Rejected, went back to v1

**Change:** Training rows where `next_kp >= 5` count 3x (`sample_weight` in `fit`). All other rows count 1x. Only training is weighted. Valid is scored as normal.

**Idea:** Only 3% of training rows are storms, so the model gets pulled toward quiet values. Making storm mistakes cost more should push it to forecast higher when a storm is coming.

| | MAE | Hit rate | False alarms |
|---|---|---|---|
| v1 @ ≥5 | 0.547 | 21.32% | 32.26% |
| Exp 2 @ ≥5 | 0.554 | 35.03% | 43.44% |
| v1 @ ≥4.4 | 0.547 | 45.18% | 51.37% |
| Exp 2 @ ≥4.4 | 0.554 | 59.39% | 65.18% |

**What happened:** At ≥5, hit rate went up a lot, but false alarms went up too. To check if it was actually better, I compared it to v1 at the same false alarm rate. Exp 2's 43.44% false alarms falls between v1's ≥5 and ≥4.4 rows. Estimating v1's hit rate at that point gives about 35.2%, and Exp 2 got 35.03%. Basically the same.

So weighting didn't make the model better at telling storms apart from quiet times. It just shifted all forecasts up, which is the same thing as lowering the threshold on v1. And MAE got a little worse (0.547 to 0.554).

**Takeaway:** If a change raises hits and false alarms together, compare at the same false alarm rate before calling it an improvement.