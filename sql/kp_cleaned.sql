-- Clean Kp: one row per minute.
-- Each minute appears in ~6 overlapping hourly files; keep the copy from the
-- newest file (largest "$path"), which holds NOAA's latest revision.
-- time_tag (text) is converted to observed_at (timestamp) for time math and joins.

CREATE VIEW aurora_cast.kp_clean AS
WITH numbered AS (
  SELECT
    date_parse(time_tag, '%Y-%m-%dT%H:%i:%s') AS observed_at,
    kp_index,
    estimated_kp,
    kp,
    ROW_NUMBER() OVER (PARTITION BY time_tag ORDER BY "$path" DESC) AS rn
  FROM aurora_cast.kp_raw
)
SELECT observed_at, kp_index, estimated_kp, kp
FROM numbered
WHERE rn = 1;