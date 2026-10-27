-- Clean magnetic field: one row per minute, ACTIVE spacecraft only (usually SOLAR1).
-- Spacecraft are never mixed. Minutes with no active reading are left as gaps
-- (rare for mag: ~0.3%, vs ~21% for wind).
-- Times are rounded to the minute (date_trunc) so they line up with kp_clean.

CREATE VIEW aurora_cast.mag_clean AS
WITH numbered AS (
    SELECT
        date_trunc('minute', date_parse(time_tag, '%Y-%m-%dT%H:%i:%s')) AS observed_at,
        source,
        bt,
        bz_gsm,
        by_gsm,
        overall_quality,
        ROW_NUMBER() OVER (
            PARTITION BY date_trunc('minute', date_parse(time_tag, '%Y-%m-%dT%H:%i:%s'))
            ORDER BY "$path" DESC
        ) AS rn
    FROM aurora_cast.mag_raw
    WHERE active = true
)
SELECT observed_at, source, bt, bz_gsm, by_gsm, overall_quality
FROM numbered
WHERE rn = 1;