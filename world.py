import yaml

from common import log, Singleton


valid_directions = ('n', 's', 'e', 'w', 'ne', 'nw', 'se', 'sw', 'u', 'd', 'enter', 'leave')


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
        self.config = {
            'verbose': True,
        }
        self.rooms = {}
        self.doors = {}
        self.areas = {}

    def load(self, config_root):
        # Loading a world always starts from a cleanly-initialized object
        self.__init__()

        log(f'Using config root [{config_root}]', 'STARTUP')

        # Check for a config file and overwrite defaults with any parameters
        config_file = (config_root / 'config.yaml')
        if config_file.exists():
            with config_file.open() as f:
                try:
                    self.config.update(yaml.safe_load(f)['config'])
                except KeyError:
                    log('Server config file must have configuration parameters as a child of a single element named <config>', exit_code=1)

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

    def load_area(self, area_id, name=None, rooms={}, doors={}):
        if not name:
            name = area_id

        area = {
            'name': name,
            'rooms': {},
            'doors': {},
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

        self.areas[area_id] = area
        self.rooms.update(area['rooms'])
        self.doors.update(area['doors'])


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
        self.target = canonical_id(area_id, target)
        self.door = canonical_id(area_id, door) if door else None


class Door:
    def __init__(self, area_id, door_id, closed=True, locked=False):
        self.id = door_id
        self.area_id = area_id
        self.closed = closed
        self.locked = locked
