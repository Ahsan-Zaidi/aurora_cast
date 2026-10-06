import requests
import sqlite3

URL = 'https://services.swpc.noaa.gov/json/planetary_k_index_1m.json'

response = requests.get(URL, timeout=10)
response.raise_for_status()
data = response.json()

print(f'Got {len(data)} records')

latest = data[-1]

print(f'Latest reading at {latest["time_tag"]} UTC')
print(f'Estimated Kp: {latest["estimated_kp"]}')

con = sqlite3.connect('aurora_cast.db')
cur = con.cursor()

for row in data:
    cur.execute("INSERT OR IGNORE INTO kp_readings(observed_at_utc, estimated_kp, kp_index, kp) VALUES (?, ?, ?, ?)", (row['time_tag'], row['estimated_kp'], row['kp_index'], row['kp']))

con.commit()
con.close()