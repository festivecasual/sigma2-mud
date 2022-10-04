from commands.commands import Alias, Command, CommandStatus
from world import World, directions, valid_directions


@Command(priority=1)
def look(message):
    w = World()
    room = w.rooms[message.speaker.location]
    message.speaker.send_line(f'[{room.name}]')
    message.speaker.send_line(room.desc)
    message.speaker.send_line(f'Exits: {", ".join(directions[i] for i in room.exits)}')
    return CommandStatus.SUCCESS


@Alias(target='go', priority=1)
def north(message):
    pass


@Alias(target='go', priority=1)
def n(message):
    pass


@Alias(target='go', priority=1)
def nw(message):
    pass


@Alias(target='go', priority=1)
def northwest(message):
    pass


@Alias(target='go', priority=1)
def ne(message):
    pass


@Alias(target='go', priority=1)
def northeast(message):
    pass


@Alias(target='go', priority=1)
def sw(message):
    pass


@Alias(target='go', priority=1)
def southwest(message):
    pass


@Alias(target='go', priority=1)
def s(message):
    pass


@Alias(target='go', priority=1)
def south(message):
    pass


@Alias(target='go', priority=1)
def se(message):
    pass


@Alias(target='go', priority=1)
def southeast(message):
    pass


@Alias(target='go', priority=1)
def e(message):
    pass


@Alias(target='go', priority=1)
def east(message):
    pass


@Alias(target='go', priority=1)
def w(message):
    pass


@Alias(target='go', priority=1)
def west(message):
    pass


@Alias(target='go', priority=1)
def enter(message):
    pass


@Alias(target='go', priority=2)
def leave(message):
    pass


@Command(priority=1)
def go(message):
    direction_to_check = message.mapped_verb if message.mapped_verb != 'go' else None
    direction_to_go = None
    if direction_to_check in valid_directions:
        direction_to_go = direction_to_check
    else:
        for direction in valid_directions:
            if directions[direction] == direction_to_check:
                direction_to_go = direction
                break
    if direction_to_go is None:
        message.speaker.send_line('That is not a direction you can go.')
        return CommandStatus.FAILURE

    w = World()
    room = w.rooms[message.speaker.location]
    exit_ = room.exits.get(direction_to_go)
    if exit_ is None:
        message.speaker.send_line('You cannot go in that direction.')
        return CommandStatus.FAILURE
    if exit_.door and (exit_.door.closed is True or exit_.door.locked is True):
        message.speaker.send_line('That direction is closed.')
        return CommandStatus.FAILURE

    if message.speaker.move(room, exit_.target) is False:
        return CommandStatus.FAILURE

    return CommandStatus.SUCCESS
