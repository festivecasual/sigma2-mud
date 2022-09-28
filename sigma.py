from pathlib import Path
import asyncio
import argparse

import websockets

from world import World
from common import log
from network import TelnetConnection, WebsocketConnection, websocket_handler


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
    
    log(f"Running websocket server on {w.config['websocket_host'] or '*'}:{w.config['websocket_port']}", 'SERVER')
    websocket_server = await websockets.serve(
        websocket_handler,
        w.config['websocket_host'],
        w.config['websocket_port'],
        create_protocol=WebsocketConnection
    )
    awaitables.append(websocket_server.serve_forever())

    await asyncio.gather(*awaitables)


asyncio.run(main())
