-- Raw solar wind (plasma) readings from NOAA SWPC (rtsw_wind_1m), one row per line of each file.
-- Several spacecraft per minute (SOLAR1 active, IMAP backup): a reading is unique by (time_tag, source).
-- Contains duplicates: every hourly file holds the full rolling window.
-- fetch_date = the day the file was FETCHED (from the date= folder), not the reading's date.

CREATE EXTERNAL TABLE aurora_cast.wind_raw (
  time_tag           string,
  source             string,
  active             boolean,
  proton_speed       double,
  proton_temperature double,
  proton_density     double,
  overall_quality    int
)
PARTITIONED BY (fetch_date string)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://aurora-cast-data-ahsan-v1/raw/feed=wind/'
TBLPROPERTIES (
  'projection.enabled'                  = 'true',
  'projection.fetch_date.type'          = 'date',
  'projection.fetch_date.format'        = 'yyyy-MM-dd',
  'projection.fetch_date.range'         = '2026-10-19,NOW',
  'projection.fetch_date.interval'      = '1',
  'projection.fetch_date.interval.unit' = 'DAYS',
  'storage.location.template'           = 's3://aurora-cast-data-ahsan-v1/raw/feed=wind/date=${fetch_date}/'
);