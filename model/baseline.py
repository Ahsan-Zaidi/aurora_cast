from split import load_splits


def main():
    train, valid, test = load_splits()

    forecast = valid['kp']
    error = (valid['next_kp'] - forecast).abs()
    mae = error.mean()

    print(f'Persistence MAE (valid): {mae:.3f}')

    exact = (forecast == valid['next_kp']).mean() * 100
    print(f'Exactly right: {exact:.1f}% of blocks')


if __name__ == '__main__':
    main()