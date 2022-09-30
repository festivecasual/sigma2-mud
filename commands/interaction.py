from commands.commands import Alias, Command, CommandStatus
from world import World, directions


@Command
def look(message):
    w = World()
    room = w.rooms[message.speaker.location]
    message.speaker.send_line(f'[{room.name}]')
    message.speaker.send_line(room.desc)
    message.speaker.send_line(f'Exits: {",".join(directions[i] for i in room.exits)}')
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
def enter(message):
    pass

@Alias(target='go', priority=1)
def leave(message):
    pass


@Command(priority=1)
def go(message):
    message.speaker.send_line('go called!')
    return CommandStatus.SUCCESS
