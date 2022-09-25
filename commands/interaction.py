from commands.commands import Alias, Command



@Command
def look(message):
    message.speaker.send_line( str(message.speaker.location.desc))
    return  str(message.speaker.location)

@Command(priority=1)
def go(message):
    return