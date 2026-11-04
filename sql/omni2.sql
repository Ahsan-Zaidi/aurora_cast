-- Historical hourly solar wind from NASA OMNI2, 1995 onward (loaded by load_omni.py).
-- One file per year under year=YYYY/; data_year is the partition (integer projection).
-- Fill values are null. Field names match wind_clean / mag_clean.

CREATE EXTERNAL TABLE aurora_cast.omni2 (
    hour_start string,
    bt double,
    by_gsm double,
    bz_gsm double,
    proton_temperature double,
    proton_density double,
    proton_speed double
)
PARTITIONED BY (data_year int)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://aurora-cast-data-ahsan-v1/history/source=omni2/'
TBLPROPERTIES (
    'projection.enabled'            = 'true',
    'projection.data_year.type'     = 'integer',
    'projection.data_year.range'    = '1995,2030',
    'storage.location.template'     = 's3://aurora-cast-data-ahsan-v1/history/source=omni2/year=${data_year}/'
)