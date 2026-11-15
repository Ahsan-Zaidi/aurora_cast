# AuroraCast: Experiments Log

Baseline for comparison: **Model v1** (validation set, 2016–2019, 197 storms)

| | MAE | Hit rate | False alarms |
|---|---|---|---|
| Persistence | 0.618 | 41.62% | 58.59% |
| v1 @ ≥5 | 0.547 | 21.32% | 32.26% |
| v1 @ ≥4.33 | 0.547 | 49.75% | 54.84% |

Note: 1 storm ≈ 0.5% of hit rate on valid, so small changes are noise.

---

## Experiment 1: Southward Bz × speed interaction
**Date:** 2026-11-15
**Status:** Rejected, reverted to v1

**What changed:** Added two engineered features:
- `south_bz = (-min_bz).clip(lower=0)` (southward Bz only; northward set to 0)
- `speed_x_south_bz = south_bz * avg_speed` (approximates energy coupling into the magnetosphere)

**Why:** Physically, storms are driven by fast solar wind with strong southward Bz.
The hypothesis was that giving the model this product directly would help.

**Results (valid):**

| | MAE | Hit rate | False alarms |
|---|---|---|---|
| v1 @ ≥5 | 0.547 | 21.32% | 32.26% |
| Exp 1 @ ≥5 | 0.547 | 21.83% | 29.51% |
| v1 @ ≥4.33 | 0.547 | 49.75% | 54.84% |
| Exp 1 @ ≥4.33 | 0.547 | 47.72% | 55.24% |

**Decision:** No real gain. MAE was unchanged, and the storm metrics moved by
only a few storms in mixed directions (noise).

**Why it didn't help:** Tree models can already learn the interaction by splitting
on `min_bz` and then `avg_speed`. The engineered feature gave them nothing new.
Simpler model wins.

**Lesson:** Hand-built interaction features help linear models more than trees.
Before adding a feature, ask whether the model can already build it from what it has.