-- Raw Kp readings from NOAA SWPC (planetary_k_index_1m), one row per line of each file.
-- Contains duplicates: every hourly file holds the full ~6-hour window.
-- fetch_date = the day the file was FETCHED (from the date= folder), not the reading's date.
-- Run once in Athena (us-east-1). Dropping this table never deletes the S3 files.


CREATE EXTERNAL TABLE aurora_cast.kp_raw (
  time_tag     string,
  kp_index     int,
  estimated_kp double,
  kp           string
)
PARTITIONED BY (fetch_date string)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://aurora-cast-data-ahsan-v1/raw/feed=kp/'
TBLPROPERTIES (
  'projection.enabled'                  = 'true',
  'projection.fetch_date.type'          = 'date',
  'projection.fetch_date.format'        = 'yyyy-MM-dd',
  'projection.fetch_date.range'         = '2026-10-19,NOW',
  'projection.fetch_date.interval'      = '1',
  'projection.fetch_date.interval.unit' = 'DAYS',
  'storage.location.template'           = 's3://aurora-cast-data-ahsan-v1/raw/feed=kp/date=${fetch_date}/'
);