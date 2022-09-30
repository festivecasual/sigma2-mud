from commands.commands import Alias, Command, CommandStatus


@Command
def look(message):
    message.speaker.send_line( str(message.speaker.location.desc))
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
