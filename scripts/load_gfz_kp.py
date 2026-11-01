import requests


GFZ_URL = "https://kp.gfz.de/fileadmin/files_for_gfz_cms/Kp_ap_since_1932.txt"


def extract_data(url):
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.text


def parse_kp(text):
    results = []
    for line in text.splitlines():
        if line.startswith('#'):
            continue
        parts = line.split()
        hour = int(float(parts[3]))
        kp = float(parts[7])
        if kp == -1:
            kp = None
        ap = int(parts[8])
        if ap == -1:
            ap = None
        record = {
            'block_start': f'{parts[0]}-{parts[1]}-{parts[2]}T{hour:02d}:00:00',
            'kp': kp,
            'ap': ap,
            'd_flag': int(parts[9])
        }
        results.append(record)
    return results


def main():
    text = extract_data(GFZ_URL)
    gfz_data = parse_kp(text)
    print(len(gfz_data))
    missing_kp = sum(1 for record in gfz_data if record['kp'] is None)
    print(f'Missing kp: {missing_kp}')
    missing_ap = sum(1 for record in gfz_data if record['ap'] is None)
    print(f'Missing ap: {missing_ap}')
    print(gfz_data[0])
    print(gfz_data[-1])


if __name__ == '__main__':
    main()

