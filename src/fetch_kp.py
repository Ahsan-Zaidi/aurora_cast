import requests

URL = 'https://services.swpc.noaa.gov/json/planetary_k_index_1m.json'

response = requests.get(URL, timeout=10)
response.raise_for_status()
data = response.json()

print(f'Got {len(data)} records')

latest = data[-1]

print(f'Latest reading at {latest['time_tag']} UTC')
print(f'Estimated Kp: {latest['estimated_kp']}')