import requests
from datetime import datetime, timedelta


OMNI_URL = "https://cdaweb.gsfc.nasa.gov/pub/data/omni/low_res_omni/omni2_2024.dat"


def extract_data(url):
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.text


def clean(value, fill):
    if value == fill:
        return None
    return value


def parse_omni(text):
    result = []
    for line in text.splitlines():
        parts = line.split()
        year = int(parts[0])
        day_of_year = int(parts[1])
        hour = int(parts[2])

        start_of_year = datetime(year, 1, 1)
        moment = start_of_year + timedelta(days=day_of_year - 1, hours=hour)
        hour_start = moment.isoformat()

        record = {
            'hour_start': hour_start,
            'bt': clean(float(parts[8]), 999.9),
            'by_gsm': clean(float(parts[15]), 999.9),
            'bz_gsm': clean(float(parts[16]), 999.9),
            'proton_temperature': clean(float(parts[22]), 9999999.0),
            'proton_density': clean(float(parts[23]), 999.9),
            'proton_speed': clean(float(parts[24]), 9999.0)
        }

        result.append(record)

    return result


def main():
    text = extract_data(OMNI_URL)
    omni_data = parse_omni(text)
    print(len(omni_data))
    missing_bt = sum(1 for record in omni_data if record['bt'] is None)
    print(f'Missing bt: {missing_bt}')
    missing_proton_speed = sum(1 for record in omni_data if record['proton_speed'] is None)
    print(f'Missing proton_speed: {missing_proton_speed}')
    print(omni_data[0])
    print(omni_data[-1])

if __name__ == '__main__':
    main()