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

---

## Experiment 3: Last-hour solar wind
**Date:** 2026-11-17
**Result:** Accepted, this is now **Model v2**

**Change:** Added the last hour of each block (the hour where `hour % 3 = 2`) as new features: `last_speed`, `last_bz`, `last_bt`, `last_density`. These come from a new view, `training_blocks_v2` (`sql/training_blocks_v2.sql`). The v1 view is untouched. `load_splits()` now takes a `path` so train.py can pick which CSV to load.

**Idea:** The 3-hour averages mix in wind from up to 3 hours ago. The most recent hour is closer to what hits Earth next, so it should be more useful, especially for fast-changing values like Bz.

Missing values went up a little since each one depends on a single hour instead of three (speed 458 to 594, bz 426 to 510, bt 418 to 501, density 1,795 to 2,158). Still under 2.5% for all of them.

Added one at a time, each on top of the last:

| | MAE | Hit @5 | FA @5 | Hit @4.33 | FA @4.33 |
|---|---|---|---|---|---|
| v1 | 0.547 | 21.32% | 32.26% | 49.75% | 54.84% |
| + last_speed | 0.545 | 22.34% | 30.16% | 48.22% | 56.42% |
| + last_bz | 0.527 | 21.32% | 33.33% | 51.78% | 55.07% |
| + last_bt | 0.523 | 21.83% | 29.51% | 51.78% | 55.46% |
| + last_density | 0.519 | 22.84% | 27.42% | 54.82% | 54.04% |

**What happened:** Each `last_` feature took over from its 3-hour version in the importance ranking (for example, `avg_speed` dropped from 0.174 to 0.007 once `last_speed` was in). The model clearly prefers the most recent reading. `last_speed` barely helped on its own though. Speed doesn't change much within 3 hours, so it was mostly the same info. `last_bz` gave the biggest MAE drop, which makes sense since Bz can flip north/south within an hour.

Compared to v1, MAE went from 0.547 to 0.519 (about 5% better). MAE is averaged over all 11,688 valid rows, so a 0.028 drop is much harder to get by luck than a few storms' change in hit rate. The storm numbers also all moved the right way together: about 10 more storms caught at 4.33 with fewer false alarms. That's different from Experiment 2, which only slid along the trade-off.

**Removal test:** After adding all four, the 3-hour features and `prev_kp` were near zero importance, so I tried a model with only `kp` + the four `last_` features.

| | MAE | Hit @5 | FA @5 | Hit @4.33 | FA @4.33 |
|---|---|---|---|---|---|
| 10 features | 0.519 | 22.84% | 27.42% | 54.82% | 54.04% |
| 5 features | 0.520 | 22.84% | 30.77% | 52.28% | 55.22% |

MAE was the same, but the storm numbers got a bit worse everywhere. My guess is the 3-hour features act as a backup: if the last hour is missing, the other two hours still give a value, and data goes missing most often during storms. 197 storms isn't enough to prove that, but the results point that way. Kept all 10 since the backups cost nothing extra to compute.

**Takeaways:**
- Low importance doesn't always mean useless. A feature can matter in the rare cases where its partner is missing.
- Importance shows what the model uses, not how much a feature helps. `last_speed` jumped to #2 but barely moved MAE.

**For the live pipeline:** The live data is 1-minute readings, not hourly. To match training, "last hour" will need to be built the same way OMNI builds its hourly values (averaging the last 60 minutes of the block).

**New baseline:** v2 (MAE 0.519). Future experiments get compared against this.

---

## Final test result (Model v2)
**Date:** 2026-11-17
**Script:** `model/evaluate_test.py` (run once)

**Setup:** Everything was locked in on validation before running: v2 features, same model settings (`random_state=42`), and two thresholds (4.33 as the main one, 5 as the plain storm definition). The model was retrained on train + valid (1995-2019, 73,048 rows) so it learns from the most recent data before 2020. Then it was scored once on test.

Test set: 2020-2026, 19,967 blocks, 507 storms (1 storm is about 0.2% of hit rate).

| | MAE | Hit rate | False alarms |
|---|---|---|---|
| Persistence | 0.646 | 51.68% | 48.32% |
| v2 @ ≥4.33 | 0.536 | 69.23% | 49.64% |
| v2 @ ≥5 | 0.536 | 44.38% | 23.99% |

**What it means:**
- MAE is 17% lower than persistence. On validation it was 16% lower. The improvement held up on data the model never saw, so the experiments didn't overfit to validation.
- At 4.33, the model catches about 89 more storms than persistence with about the same false alarm rate.
- At 5, it catches a few fewer storms than persistence but has half the false alarms. When it says storm, it's usually right.
- Test MAE (0.536) is a bit higher than validation (0.519). That's expected, since 2020-2026 covers the active part of the solar cycle and validation was near solar minimum. Persistence got worse by about the same amount (0.618 to 0.646).

**Caveats:**
- The 4.33 threshold was picked with a model trained on 1995-2015 only. The final model was retrained on more data, which could shift its forecasts a little.
- These results use GFZ definitive Kp. NOAA's live Kp runs about 0.19 higher on average, so live performance may differ (training-serving skew).

The test set is now used. Any future model changes will need new data to evaluate honestly.