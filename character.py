import uuid
from common import log


class Character:
    def __init__(self, name=None, location=None, stats={}):
        self.name = name
        
        from world import World
        self.location = location or World().config['default_location']
        
        self.load_stats(stats)

    def load_stats(self, stats):
        self.level = stats.get('level', 1)
        self.hp = stats.get('hp', self.level * 15)

    id = property(lambda self: None)

    def move(self, start_room, dest_room):
        from world import Room
        if not isinstance(start_room, Room) or not isinstance(dest_room, Room):
            log(f"One or more rooms is invalid for move attempt. Attempted move failed.", "CHARACTER")
            return False
        if self.location != start_room.canonical_id:
            log(f"Character {self.id} is not in room {start_room.canonical_id}. Attempted move failed.", "CHARACTER")
            return False
        if not start_room.remove_character(self):
            log(f"Character {self.id} cannot be removed from room {start_room.id}. Attempted move failed", "CHARACTER")
            return False
        self.location = dest_room.canonical_id
        if not dest_room.add_character(self):
            log(f"Character {self.id} cannot be added to room {dest_room.id}. Attempted move failed", "CHARACTER")

        # TODO: call look
        return True


class Denizen(Character):
    def __init__(self, area_id, source_id, name, location, stats={}, keywords=[], short=None, desc=None):
        super().__init__(name, location, stats)

        self.area_id = area_id
        self.source_id = source_id

        self.uuid = str(uuid.uuid4())

        self.keywords = keywords
        self.short = short or name
        self.desc = desc or short or name

    id = property(lambda self: f'{self.source_id}@{self.uuid}')


class Player(Character):
    def __init__(self, connection, name, location=None, stats={}):
        super().__init__(name, location, stats)

        self.connection = connection

    def to_proto(self):
        return {
            'location': self.location,
            'stats': {
                'level': self.level,
                'hp': self.hp,
            },
        }

    id = property(lambda self: self.name)

    def send_line(self, line):
        self.connection.write_line(line)
