import asyncio
import string

from common import log
from world import World


class BaseConnection(asyncio.Protocol):
    def connection_made(self, transport):
        self.transport = transport
        self.player = None
        self.state = 'welcome'
        self.world = World()

        welcome_message = self.world.config['welcome_message']
        if type(welcome_message) == list:
            self.send(*welcome_message)
        else:
            self.send(welcome_message)
        self.send_prompt(2)

    def send(self, *txts):
        raise NotImplementedError()
    
    def send_line(self, line=''):
        self.send(line + '\r\n')

    def send_prompt(self, lines_before=1):
        for _ in range(lines_before):
            self.send_line()

        if self.state == 'welcome':
            self.send('Enter your name (or + to create a new character): ')
        elif self.state == 'password' or self.state == 'create_password':
            self.send('Your password: ')
        elif self.state == 'create_username':
            self.send('Enter the name you will use: ')
        elif self.state == 'create_password_again':
            self.send('Please re-enter your password: ')
        elif self.state == 'playing':
            self.send('> ')

    def process(self, line):
        getattr(self, 'process_' + self.state)(line)
    
    def process_welcome(self, line):
        if line == '+':
            self.send_line('Welcome!')
            self.state = 'create_username'
            self.send_prompt()
            return

        self.player = self.world.retrieve_player_data(line)
        if not self.player:
            self.send_line('- That name is not known here.')
            self.send_prompt()
            return

        self.state = 'password'
        self.send_prompt(0)

    def process_password(self, line):
        if line == '':
            self.state = 'welcome'
            self.send_prompt()
            return

        self.send_line('- Incorrect password.')
        self.send_prompt()

    def process_create_username(self, line):
        if line == '':
            self.send_prompt()
            return
        
        self.player = line
        self.state = 'create_password'
        self.send_prompt(0)

    def process_create_password(self, line):
        if line == '':
            self.send_prompt()
            return
        
        self.player = (self.player, line)
        self.state = 'create_password_again'
        self.send_prompt(0)
    
    def process_create_password_again(self, line):
        if line != self.player[1]:
            self.send_line('- Passwords do not match.')
            self.state = 'create_password'
            self.send_prompt()
            return
        
        self.state = 'playing'
        self.send_prompt()
    
    def process_playing(self, line):
        self.send_line(f'What do you mean, "{line}"?  That is ridiculous.')
        self.send_prompt()


# Byte codes for Telnet escape sequences
class Telnet:
    IAC           = 255
    WILL          = 251
    WONT          = 252
    DO            = 253
    DONT          = 254
    IAC_VERBS     = (WILL, WONT, DO, DONT)    
    SE            = 240
    SB            = 250
    ECHO          = 1
    SGA           = 3
    LINEMODE      = 34

Telnet.known_symbols = {getattr(Telnet, symbol) : symbol for symbol in dir(Telnet) if type(getattr(Telnet, symbol)) == int}
Telnet.to_text = lambda byte: Telnet.known_symbols.get(byte, str(byte))


# ANSI escape sequences
class Ansi:
    CSI           = bytes([0x1B, ord('[')])
    LEFT_ARROW    = CSI + b'D'
    HOME_KEY      = CSI + b'H'
    HOME_MOVE     = CSI + b'1~'


format_codes = {
    '{reset}': b'\x1B[0m',
    '{black}': b'\x1B[30m',
    '{red}': b'\x1B[31m',
    '{green}': b'\x1B[32m',
    '{yellow}': b'\x1B[33m',
    '{blue}': b'\x1B[34m',
    '{magenta}': b'\x1B[35m',
    '{cyan}': b'\x1B[36m',
    '{white}': b'\x1B[37m',
    '{default}': b'\x1B[39m',
    '{bold}': b'\x1B[1m',
}


class TelnetConnection(BaseConnection):
    all_bufferable_characters = string.ascii_letters + string.digits + string.punctuation + ' '

    def connection_made(self, transport):
        super(TelnetConnection, self).connection_made(transport)

        self.peername = transport.get_extra_info('peername')[0] + ':' + str(transport.get_extra_info('peername')[1])
        log(f'Telnet connection received from {self.peername}', 'CLIENT')

        self.buffer = b''
        self.ansi_escape = b''
        self.oob = b''

        # Inform client that we will remote echo
        self.transport.write(bytes([Telnet.IAC, Telnet.WILL, Telnet.ECHO]))

        # Tell client we will suppress "go ahead" operation
        self.transport.write(bytes([Telnet.IAC, Telnet.WILL, Telnet.SGA]))

        # Disable line buffering
        self.transport.write(bytes([Telnet.IAC, Telnet.WONT, Telnet.LINEMODE]))

    def data_received(self, data):
        for byte in data:
            if byte == Telnet.IAC:   # Byte is an "Is A Command" escape byte
                if not self.oob:   # IAC received while previously being in-band
                    self.oob += bytes([Telnet.IAC])
                elif len(self.oob) == 1:   # We just switched to out-of-band (OOB) but now see it's an escaped IAC
                    # Switch back to in-band and ignore the IAC since we trash anything above 127
                    self.oob = b''
                else:   # If we strangely receive an IAC during another OOB sequence, discard the previous OOB and restart
                    self.oob = b''
                    self.oob += bytes([Telnet.IAC])
            elif self.oob:   # We are OOB and receive a byte besides IAC
                self.oob += bytes([byte])   # Buffer the byte regardless of its value
                if len(self.oob) == 3 and self.oob[1] in Telnet.IAC_VERBS:   # Standard IAC sequence
                    #log(f'Telnet IAC from {self.peername} > ' + ' '.join([Telnet.to_text(i) for i in self.oob]), 'CLIENT', trivial=True)
                    self.oob = b''
                elif byte == Telnet.SE:   # End of a subnegotiation sequence
                    #log(f'Telnet IAC-SB from {self.peername} > ' + ' '.join([Telnet.to_text(i) for i in self.oob]), 'CLIENT', trivial=True)
                    self.oob = b''
            elif byte < 128:
                if self.ansi_escape:   # We are in the middle of processing an ANSI escape sequence
                    self.ansi_escape += bytes([byte])   # Buffer the byte regardless of its value
                    if len(self.ansi_escape) > 2 and (0x40 <= byte <= 0x7E):   # We have reached a terminating character
                        if self.ansi_escape == Ansi.LEFT_ARROW:   # Process a left arrow as a backspace if we have a non-empty buffer
                            if len(self.buffer) > 0:
                                self.transport.write(b'\b \b')   # Send a space to make sure the wipe occurs
                                self.buffer = self.buffer[:-1]
                        elif self.ansi_escape == Ansi.HOME_KEY or self.ansi_escape == Ansi.HOME_MOVE:   # Process a home key press as a line wipe
                            self.transport.write(b'\b' * len(self.buffer) + b' ' * len(self.buffer) + b'\b' * len(self.buffer))
                            self.buffer = b''
                        self.ansi_escape = b''   # Reset the escape sequence buffer
                elif byte == 0x1B:   # Initiate ANSI escape handling
                    self.ansi_escape = bytes([byte])
                elif byte == ord('\b') or byte == 127:   # Process backspace (or delete) if we have a non-empty buffer
                    if len(self.buffer) > 0:
                        self.transport.write(b'\b \b')   # Send a space to make sure the wipe occurs
                        self.buffer = self.buffer[:-1]
                elif byte == ord('\n') or byte == 0:   # End of a line of text (including handling <CR> <NUL>)
                    self.transport.write(b'\r\n')
                    self.process(self.buffer.decode('ascii'))
                    self.buffer = b''
                elif self.should_buffer(byte):   # Only echo and record what we are willing to accept
                    self.transport.write(bytes([byte]) if self.state not in ('password', 'create_password', 'create_password_again') else b'*')
                    self.buffer += bytes([byte])
            else:
                pass   # Ignore null and upper-half bytes

    def should_buffer(self, byte):
        if self.state in ('welcome', 'create_username'):
            if len(self.buffer) == 0:
                return chr(byte) in (string.ascii_uppercase + '+')
            elif self.state != 'welcome' or self.buffer[0] != ord('+'):
                return chr(byte) in string.ascii_letters
            else:
                return False
        else:
            return chr(byte) in TelnetConnection.all_bufferable_characters

    def send(self, *txts):
        for txt in txts:
            self.transport.write(format_codes.get(txt, False) or txt.encode('ascii'))
