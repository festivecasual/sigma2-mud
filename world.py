import sqlite3
import json

import yaml

from character import Denizen
from common import log, Singleton
from commands.commands import register_commands

directions = {
    'n': 'north',
    's': 'south',
    'e': 'east',
    'w': 'west',
    'ne': 'northeast',
    'nw': 'northwest',
    'se': 'southeast',
    'sw': 'southwest',
    'u': 'up',
    'd': 'down',
    'enter': 'enter',
    'leave': 'leave',
}
valid_directions = directions.keys()


def canonical_id(area, id, only_local=False):
    components = id.split(':', 1)
    if len(components) < 2:
        return f'{area}:{id}'
    elif only_local and components[0] != area:
        log(f'External reference <{id}> provided when only a local one (in <{area}>) is valid', exit_code=1)
    else:
        return id


class World(metaclass=Singleton):
    def __init__(self):
        self.config_root = None
        self.config = {
            'verbose': False,
            'telnet_host': None,
            'telnet_port': 4000,
            'welcome_message': ['{bold}', 'Welcome to ', '{cyan}', 'sigma2-mud', '{reset}', '!'],
            'default_location': 'system:start',
        }
        self.command_register = None
        
        self.rooms = {}
        self.doors = {}
        self.areas = {}
        self.denizens = {}
        self.players = {}

        self.denizen_sources = {}

    def setup(self, config_root):
        # Setting up a world always starts from a cleanly-initialized object
        self.__init__()

        self.config_root = config_root

        log(f'Using config root [{config_root}]', 'STARTUP')

        # Check for a config file and overwrite defaults with any parameters
        config_file = config_root / 'config.yaml'
        if config_file.exists():
            with config_file.open() as f:
                try:
                    self.config.update(yaml.safe_load(f)['config'])
                except KeyError:
                    log('Server config file must have configuration parameters as a child of a single element named <config>', exit_code=1)

        # Initialize a persistent database if we don't have one already
        db_file = config_root / 'world.db'
        if not db_file.exists():
            log('No database found, initializing a blank one', 'DATABASE')
            con = sqlite3.connect(db_file)
            con.cursor().execute('CREATE TABLE players (username text primary key, password_hash text, data text)')
            con.commit()
            con.close()

        # Load each area file
        for area_file in (config_root / 'areas').glob('*.yaml'):
            log(f'Importing area from [{area_file.relative_to(config_root)}]', 'IMPORT', trivial=True)
            area = area_file.stem
            with area_file.open() as f:
                try:
                    self.load_area(area, **yaml.safe_load(f))
                except TypeError as e:
                    log(str(e), exit_code=1)

        # Resolve room exit target and door linkages
        for room_id, room in self.rooms.items():
            for direction, exit_ in room.exits.items():
                try:
                    exit_.target = self.rooms[exit_.target]
                except KeyError:
                    log(f'Unable to resolve target <{exit_.target}> (in room <{room_id}>, direction <{direction}>)', exit_code=1)
                if not exit_.door:
                    continue
                try:
                    exit_.door = self.doors[exit_.door]
                except KeyError:
                    log(f'Unable to resolve door <{exit_.door}> (from room <{room_id}>, direction <{direction}>)', exit_code=1)

        # Ensure the default location is available for use
        assert self.config['default_location'] in self.rooms

        self.command_register = register_commands()

    def load_area(self, area_id, name=None, rooms={}, doors={}, denizens={}):
        area = {
            'name': name or area_id,
            'rooms': {},
            'doors': {},
            'denizen_sources': {},
        }

        for room_id, room in rooms.items():
            try:
                area['rooms'][canonical_id(area_id, room_id, only_local=True)] = Room(area_id, room_id, **room)
            except TypeError as e:
                log(str(e), exit_code=1)

        for door_id, door in doors.items():
            try:
                area['doors'][canonical_id(area_id, door_id, only_local=True)] = Door(area_id, door_id, **(door or {}))
            except TypeError as e:
                log(str(e), exit_code=1)

        for denizen_id, denizen in denizens.items():
            try:
                area['denizen_sources'][canonical_id(area_id, denizen_id, only_local=True)] = (area_id, denizen_id, denizen)
            except TypeError as e:
                log(str(e), exit_code=1)

        self.areas[area_id] = area
        self.rooms.update(area['rooms'])
        self.doors.update(area['doors'])
        self.denizen_sources.update(area['denizen_sources'])

    def insert_player(self, player):
        if player.id in self.players:
            return False
        
        self.players[player.id] = player

        log(f'Successful login: <{player.name}> from {player.connection.peername}', 'LOGIN')
        # TODO: Add to room
        return True

    def remove_player(self, player):
        if player.id in self.players and self.players[player.id] == player:
            log(f'Logout: <{player.name}> from {player.connection.peername}', 'LOGOUT')
            del self.players[player.id]

    def database_connection(self):
        return sqlite3.connect(self.config_root / 'world.db')

    def retrieve_player_data(self, name):
        con = self.database_connection()
        result = con.cursor().execute('SELECT data, password_hash FROM players WHERE username = ?', (name, )).fetchone()
        con.close()

        if not result:
            return None, None, None
        else:
            return json.loads(result[0]), name, result[1]

    def save_player_data(self, player):
        con = self.database_connection()
        result = con.cursor().execute('''
            INSERT INTO players (username, data) VALUES (?, ?)
            ON CONFLICT (username) DO UPDATE SET data=excluded.data
        ''', (player.name, json.dumps(player.to_proto())))
        con.commit()
        con.close()

    def update_player_password(self, player, password_hash):
        con = self.database_connection()
        result = con.cursor().execute('UPDATE players SET password_hash=? WHERE username = ?', (password_hash, player.name))
        con.commit()
        con.close()


class Room:
    def __init__(self, area_id, room_id, name=None, desc=None, exits={}):
        if not name or not desc:
            log(f'Area <{area_id}>: Room <{room_id}>: Must have "name" and "desc" parameters', exit_code=1)

        self.id = room_id
        self.area_id = area_id
        self.name = name
        self.desc = desc
        self.exits = {}

        for direction, exit_ in exits.items():
            if not direction in valid_directions:
                log(f'Area <{area_id}>: Room <{room_id}>: Invalid exit direction: {direction}', exit_code=1)
            
            if type(exit_) == dict:
                try:
                    self.exits[direction] = Exit(area_id, room_id, direction, **exit_)
                except TypeError as e:
                    log(str(e), exit_code=1)
            else:
                self.exits[direction] = Exit(area_id, room_id, direction, target=canonical_id(area_id, exit_))


class Exit:
    def __init__(self, area_id, room_id, direction, target=None, door=None):
        if not target:
            log(f'Area <{area_id}>: Room <{room_id}>: Exit <{direction}>: Must supply a target room', exit_code=1)

        self.area_id = area_id
        self.room_id = room_id
        self.direction = direction
        self.direction_label = directions[direction]
        self.target = canonical_id(area_id, target)
        self.door = canonical_id(area_id, door) if door else None


class Door:
    def __init__(self, area_id, door_id, closed=True, locked=False):
        self.id = door_id
        self.area_id = area_id
        self.closed = closed
        self.locked = locked
