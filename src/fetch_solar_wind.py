import requests
import sqlite3

WIND_URL = 'https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json'
MAG_URL = 'https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json'

wind_response = requests.get(WIND_URL, timeout=10)
wind_response.raise_for_status()
wind_data = wind_response.json()

mag_response = requests.get(MAG_URL, timeout=10)
mag_response.raise_for_status()
mag_data = mag_response.json()

print(f'Got {len(wind_data)} wind records.')
print(f'Got {len(mag_data)} magnetic records.')

latest_wind = wind_data[0]
latest_mag = mag_data[0]

print(f'Latest reading for wind record at {latest_wind["time_tag"]} UTC.')
print(f'Source {latest_wind["source"]}.')
print(f'Status {latest_wind["active"]}.')
print(f'Latest proton speed {latest_wind["proton_speed"]} km/s.')
print(f'Latest proton temperature {latest_wind["proton_temperature"]} K.')
print(f'Latest proton density {latest_wind["proton_density"]} per/cm^3.')
print(f'Overall quality for latest wind record {latest_wind["overall_quality"]}.')

print(f'Latest reading for magnetic record at {latest_mag["time_tag"]} UTC.')
print(f'Source {latest_mag["source"]}.')
print(f'Status {latest_mag["active"]}.')
print(f'Latest total field strength: {latest_mag["bt"]} nT.')
print(f'Latest North/South field component {latest_mag["bz_gsm"]} nT.')
print(f'Latest East/West field component {latest_mag["by_gsm"]} nT.')
print(f'Overall quality for latest mag record {latest_mag["overall_quality"]}')

con = sqlite3.connect('aurora_cast.db')
cur = con.cursor()

for row in wind_data:
    cur.execute(
        "INSERT OR IGNORE INTO rtsw_wind(observed_at_utc, source, active, proton_speed, proton_temp, proton_density, overall_quality) VALUES (?, ?, ?, ?, ?, ?, ?)", 
        (row["time_tag"], row["source"], row["active"], row["proton_speed"], row["proton_temperature"], row["proton_density"], row["overall_quality"]))

con.commit()

for row in mag_data:
    cur.execute(
        "INSERT OR IGNORE INTO rtsw_mag(observed_at_utc, source, active, bt, bz_gsm, by_gsm, overall_quality) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (row["time_tag"], row["source"], row["active"], row["bt"], row["bz_gsm"], row["by_gsm"], row["overall_quality"]))

con.commit()

con.close()