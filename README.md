# AuroraCast

AuroraCast forecasts the geomagnetic Kp index for the next 3-hour block using solar wind data measured upstream of Earth. It runs on AWS: an hourly pipeline collects live NOAA data, 30 years of history sit in S3 and are queried with Athena, and a gradient boosting model makes the forecast.

On a held-out test set (2020 to mid-October 2026), the model's error is 17% lower than the standard "persistence" baseline, and at its chosen threshold it catches about 89 more storms with the same false alarm rate.

## Why Kp

Kp measures how disturbed Earth's magnetic field is, on a scale from 0 to 9. At Kp 5 and above, NOAA calls it a geomagnetic storm (G1 at Kp 5, up to G5 at Kp 9).

Storms are what people usually notice as aurora, but they also degrade HF radio propagation, throw off GPS accuracy and stress power grids. I started this project wanting to know ahead of time when radio conditions would go bad and when the aurora might be visible. Both come down to forecasting Kp.

## Results

All numbers are on the **test set** (2020 to mid-October 2026: 19,967 blocks, 507 storms). It was run once, after every decision had been made on validation data. The test period stops in mid-October because that's where the OMNI solar wind data currently ends.

| | MAE | Hit rate | False alarms |
|---|---|---|---|
| Persistence (next Kp = current Kp) | 0.646 | 51.68% | 48.32% |
| **AuroraCast @ ≥4.33** | **0.536** | **69.23%** | 49.64% |
| AuroraCast @ ≥5 | 0.536 | 44.38% | 23.99% |

- **MAE**: average error in Kp units. Lower is better.
- **Hit rate**: share of real storms (Kp ≥ 5) that were forecast.
- **False alarms**: share of storm forecasts where no storm happened.

The model predicts a number, not a yes/no, so "storm" depends on the cutoff. At ≥4.33, hits and false alarms are about balanced and both beat persistence. At ≥5, the model is more cautious: it misses more storms but has half the false alarms. I report both instead of just the better-looking one.

The improvement over persistence was 16% on validation and 17% on test. That's the main sign the experiments didn't just overfit to the validation years.

## How it works

```
NOAA live feeds ──► Lambda (hourly) ──► S3 raw/ ──┐
                                                  ├──► Athena views ──► training table ──► model
GFZ Kp + NASA OMNI history ──► S3 history/ ───────┘
```

### Data collection

- **Live:** A Lambda function (`src/pipeline.py`, Python 3.14) runs every hour on an EventBridge schedule. It saves four NOAA SWPC feeds to S3 as JSON Lines, unchanged: 1-minute Kp, real-time solar wind plasma, real-time magnetic field, and NOAA's own 3-day Kp forecast. Each feed is in its own try block, so one failing feed doesn't stop the others, and everything is logged to CloudWatch.
- **History:** Scripts in `scripts/` load GFZ's definitive Kp (back to 1932) and NASA's OMNI2 hourly solar wind (1995-2026) into S3.

S3 keys follow `raw/feed=<feed>/date=<YYYY-MM-DD>/<HHMMSS>.json`, so Athena treats feed and date as partitions (using partition projection, so there are no crawlers to run). The raw data is never modified, so it can always be reprocessed if the cleaning logic changes.

**Why hourly:** I sized the schedule from measured file sizes. Each run saves about 3.4 MB, so hourly comes to about 2.5 GB a month, compared with about 30 GB if it ran every 5 minutes. NOAA's feeds cover a rolling window (6 hours for Kp), so hourly runs still overlap and leave no gaps.

**Duplicates:** More than one spacecraft reports solar wind for the same minutes, and overlapping hourly snapshots repeat rows. Athena "clean" views remove the duplicates without touching the raw files.

### Security and cost

I kept permissions as tight as I could:
- The Lambda role can only `PutObject` under `raw/` (plus writing its own logs). It can't read or delete anything.
- My local development user can only write to `history/`. It has no read or list access and no console access.
- No access keys in code. The local key lives in a named AWS profile, and reads are done from an admin session when needed.
- The bucket has Block Public Access on and SSE-S3 encryption.
- Root has MFA, and there are two budget alerts: one for any spend at all and one monthly cap. Everything is tagged `project` so costs show up per project.

### Training table

`sql/training_blocks_v2.sql` builds one row per 3-hour block (93,015 rows) by joining GFZ Kp to OMNI solar wind for the **same** block. The target, `next_kp`, is the following block's Kp. Since the features only use data from blocks that have already ended, nothing from the future leaks in.

Features:
- `kp`, `prev_kp`: current and previous Kp
- `last_speed`, `last_bz`, `last_bt`, `last_density`: solar wind in the last hour of the block
- `avg_speed`, `min_bz`, `max_bt`, `avg_density`: the same over all 3 hours

Missing solar wind values stay as NULL on purpose. Data goes missing most often during big storms, and the model handles NULLs on its own.

### Model

A scikit-learn `HistGradientBoostingRegressor`. The data is split by time, never randomly, because neighboring blocks are nearly identical and a random split would leak answers between sets:

| Set | Years | Rows | Storms |
|---|---|---|---|
| Train | 1995-2015 | 61,360 | 3.0% |
| Validation | 2016-2019 | 11,688 | 1.7% |
| Test | 2020 to Oct 2026 | 19,967 | 2.5% |

The final model was retrained on train + validation before the single test run.

## Experiments

Full details, with tables, are in [`experiments.md`](experiments.md). In short:

| # | Idea | Result |
|---|---|---|
| 1 | Southward Bz × speed feature | Rejected. Trees can already learn that combination by splitting on both. |
| 2 | Weight storm rows 3× in training | Rejected. It raised hits and false alarms together, which is the same as lowering the threshold. |
| 3 | Add last-hour solar wind | **Accepted.** Validation MAE went from 0.547 to 0.519, and storm metrics improved with no trade-off. |

Some things I learned along the way:
- If a change raises hits and false alarms together, compare at the same false alarm rate before calling it an improvement.
- Feature importance shows what the model uses, not how much a feature helps.
- A feature with near-zero importance can still matter as a backup when its partner is missing.

## Limitations

- **Warning time is short.** The solar wind monitors sit about 1.5 million km upstream, which gives roughly 30-60 minutes of warning. A 3-hour-ahead forecast is partly predicting wind that hasn't been measured yet, so there's a ceiling on accuracy.
- **Training vs live data.** The model trains on GFZ's definitive Kp, but live Kp comes from NOAA, which runs about 0.19 higher on average. Live performance may differ from the test results.
- **The threshold was picked on the train-only model.** The final model was retrained on more data, which could shift its forecasts slightly.
- **Solar flares aren't covered.** Flare-driven radio blackouts hit with no solar wind warning, so this model can't forecast them.

## Keeping it up to date

The live feeds collect themselves, but the history doesn't:
- **GFZ Kp and OMNI2 are reloaded by hand once a month** (`scripts/load_gfz_kp.py` and `scripts/load_omni.py`). OMNI runs a few weeks behind real time, and GFZ only marks Kp as definitive after a delay, so the newest blocks show up in the training table gradually.
- Because the training table is an Athena view, new rows appear automatically after a reload. Nothing needs to be rebuilt.
- The Lambda's health can be checked in its Monitor tab and CloudWatch logs, or by looking for new files in S3 about an hour apart.

## How it got here

The project started as a local script that pulled NOAA's Kp feed into a SQLite database on my laptop. I added solar wind feeds, refactored it into extract and load functions, and added error handling and logging. The problem was that it only collected data while the laptop was on, so I moved it to AWS: Lambda, S3 and EventBridge, with SQLite dropped entirely. After that came Athena, the historical backfills, and finally the model.

## What's next

- [ ] A live prediction Lambda (container image, since scikit-learn is too big for a zip) that forecasts every block and saves the result
- [ ] Compare AuroraCast against NOAA's own forecasts, which have been collected hourly since Nov 2026
- [ ] Storm alerts via SNS
- [ ] A small dashboard hosted on S3 + CloudFront
- [ ] Infrastructure as code and CI tests

## Project layout

```
src/pipeline.py          hourly Lambda that saves NOAA feeds to S3
scripts/                 one-off and monthly history loaders (GFZ Kp, OMNI2)
sql/                     Athena tables and views, including the training table
model/
  split.py               time-based train / valid / test split
  metrics.py             MAE, hit rate, false alarm rate
  baseline.py            persistence baseline
  train.py               trains the model and scores it on validation
  evaluate_test.py       final test-set evaluation (run once)
experiments.md           log of every experiment and why it was kept or dropped
```

## Running it

Python 3.14, on Windows with PowerShell:

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

The training data isn't in the repo. Run `SELECT * FROM aurora_cast.training_blocks_v2 ORDER BY block_ts` in Athena and save the result as `data/training_blocks_v2.csv`. Then:

```
python model/train.py          # train on 1995-2015, score on validation
python model/evaluate_test.py  # final test score
```

### Deploying a pipeline change

Lambda already includes `boto3`, so the zip only needs `requests`, built for Linux:

```
pip install requests --target package --platform manylinux2014_x86_64 --only-binary=:all: --python-version 3.14
Copy-Item src\pipeline.py package\
Compress-Archive -Path package\* -DestinationPath aurora_cast_lambda.zip -Force
```

Then upload `aurora_cast_lambda.zip` in the Lambda console (Code → Upload from → .zip file) and run a test event to check that every feed saves. The first line only needs to be run once, or when `requests` changes. The local dev user can't write to `raw/`, so the pipeline has to be tested in Lambda, not locally.

## Data sources

- [NOAA Space Weather Prediction Center](https://www.swpc.noaa.gov/): live Kp, real-time solar wind and Kp forecasts
- [GFZ Potsdam](https://kp.gfz.de/): definitive Kp index since 1932
- [NASA OMNIWeb](https://omniweb.gsfc.nasa.gov/): OMNI2 hourly solar wind data
