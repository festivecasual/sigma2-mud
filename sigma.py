from pathlib import Path

from world import World


if __name__ == '__main__':
    script_root = Path(__file__).resolve().parent

    import argparse
    parser = argparse.ArgumentParser(description='Start the sigma2-mud server.')
    parser.add_argument(
        '--root',
        type=Path,
        default=(script_root / 'server'),
        help='Specify a server configuration root directory'
    )
    args = parser.parse_args()

    World().load(args.root)
