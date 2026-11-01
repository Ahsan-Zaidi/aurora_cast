-- Historical Kp from GFZ Potsdam, 3-hour blocks since 1932 (one file, replaced by load_gfz_kp.py).
-- block_start = start of the 3-hour UTC block. d_flag: 1 = definitive, 0 = preliminary.
-- Missing values are null (GFZ's -1 converted by the loader).

CREATE EXTERNAL TABLE aurora_cast.gfz_kp (
    block_start string,
    kp          double,
    ap          int,
    d_flag      int
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://aurora-cast-data-ahsan-v1/history/source=gfz_kp/';