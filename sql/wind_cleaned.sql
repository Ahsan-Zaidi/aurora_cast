-- Clean solar wind: one row per minute, ACTIVE spacecraft only (usually SOLAR1).
-- Spacecraft disagree (e.g., speed differs by ~15 km/s), so sources are never mixed.
-- Minutes with no active reading (~20%) are left as gaps on purpose; handle them in modeling.
-- Times are rounded to the minute (date_trunc) so they line up with kp_clean.

CREATE VIEW aurora_cast.wind_clean AS
WITH numbered AS (
    SELECT
        date_trunc('minute', date_parse(time_tag, '%Y-%m-%dT%H:%i:%s')) AS observed_at,
        source,
        proton_speed,
        proton_temperature,
        proton_density,
        overall_quality,
        ROW_NUMBER() OVER (
            PARTITION BY date_trunc('minute', date_parse(time_tag, '%Y-%m-%dT%H:%i:%s'))
            ORDER BY "$path" DESC
        ) AS rn
    FROM aurora_cast.wind_raw
    WHERE active = true
)
SELECT observed_at, source, proton_speed, proton_temperature, proton_density, overall_quality
FROM numbered
WHERE rn = 1;