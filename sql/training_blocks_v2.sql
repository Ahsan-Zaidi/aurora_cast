-- Training table for the Kp forecast model: one row per 3-hour block, 1995 onward.
-- Each row = the block that just ended (block_ts). The model's job is to predict next_kp,
-- the Kp of the FOLLOWING block, from what is known when this block ends.
--
-- Sources: gfz_kp (official Kp, definitive values only) and omni2 (hourly solar wind).
-- Features:
--   kp, prev_kp          Kp of this block and the one before (Kp's "memory")
--   min_bz               most southward Bz in this block (south = energy enters)
--   max_bt               strongest total field in this block (a passing eruption)
--   avg_speed            average solar wind speed in this block
--   avg_density          average density in this block
--   last_speed           most recent value of proton_speed from the last hour in the current wind_block (hour % 3 = 2)
--   last_bz              most recent value of bz_gsm from the last hour in the current wind_block (hour % 3 = 2)
--   last_bt              most recent value of bt from the last hour in the current wind_block (hour % 3 = 2)
--   last_density         most recent value of proton_density from the last hour in the current wind_block (hour % 3 = 2)
--
-- No leakage: each row joins the solar wind of the SAME block (the 3 hours that just
-- ended), never the next block, which hasn't happened yet at forecast time.
-- OMNI hours are assigned to their block by rounding down to a multiple of 3 (19:00 -> 18:00).
--
-- Rows without a definitive next_kp are excluded; as a view, it picks them up
-- automatically once GFZ finalizes them. The first row (1995) has prev_kp = NULL.
-- Missing solar wind is kept as NULL on purpose: data goes missing most often during
-- the strongest storms, and the model handles NULLs itself.

CREATE VIEW aurora_cast.training_blocks_v2 AS
WITH kp_rows AS (
    SELECT
        date_parse(block_start, '%Y-%m-%dT%H:%i:%s') AS block_ts,
        kp,
        LAG(kp)  OVER (ORDER BY block_start) AS prev_kp,
        LEAD(kp) OVER (ORDER BY block_start) AS next_kp
    FROM aurora_cast.gfz_kp
    WHERE d_flag = 1
      AND block_start >= '1995-01-01'
),
hours AS (
    SELECT
        date_parse(hour_start, '%Y-%m-%dT%H:%i:%s') AS hour_ts,
        bz_gsm,
        bt,
        proton_speed,
        proton_density
    FROM aurora_cast.omni2
    WHERE data_year BETWEEN 1995 AND 2026
),
wind_blocks AS (
    SELECT
        date_add('hour', -(hour(hour_ts) % 3), hour_ts) AS block_start,
        min(bz_gsm) AS min_bz,
        max(bt) AS max_bt,
        avg(proton_speed) AS avg_speed,
        avg(proton_density) AS avg_density,
        max(CASE WHEN hour(hour_ts) % 3 = 2 THEN proton_speed END) AS last_speed,
        max(CASE WHEN hour(hour_ts) % 3 = 2 THEN bz_gsm END) AS last_bz,
        max(CASE WHEN hour(hour_ts) % 3 = 2 THEN bt END) AS last_bt,
        max(CASE WHEN hour(hour_ts) % 3 = 2 THEN proton_density END) AS last_density
    FROM hours
    GROUP BY date_add('hour', -(hour(hour_ts) % 3), hour_ts)
)
SELECT
    k.block_ts,
    k.kp,
    k.prev_kp,
    w.min_bz,
    w.max_bt,
    w.avg_speed,
    w.avg_density,
    w.last_speed,
    w.last_bz,
    w.last_bt,
    w.last_density,
    k.next_kp
FROM kp_rows k
JOIN wind_blocks w
    ON k.block_ts = w.block_start
WHERE k.next_kp IS NOT NULL;