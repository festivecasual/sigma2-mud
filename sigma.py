from pathlib import Path
import asyncio
import argparse

from world import World
from common import log
from network import TelnetConnection


script_root = Path(__file__).resolve().parent

parser = argparse.ArgumentParser(description='Start the sigma2-mud server.')
parser.add_argument(
    '--root',
    type=Path,
    default=(script_root / 'server'),
    help='Specify a server configuration root directory'
)
args = parser.parse_args()


World().setup(args.root)


async def main():
    w = World()

    loop = asyncio.get_running_loop()

    awaitables = []

    log(f"Running telnet server on {w.config['telnet_host'] or '*'}:{w.config['telnet_port']}", 'SERVER')
    telnet_server = await loop.create_server(lambda: TelnetConnection(), w.config['telnet_host'], w.config['telnet_port'])
    awaitables.append(telnet_server.serve_forever())
    
    await asyncio.gather(*awaitables)


asyncio.run(main())
