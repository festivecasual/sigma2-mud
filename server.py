import asyncio
import string
import ast

from common import log


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
    LINEMODE      = 34


# ANSI escape sequences
class Ansi:
    CSI           = bytes([0x1B, ord('[')])
    LEFT_ARROW    = CSI + b'D'
    HOME          = CSI + b'1~'


bufferable_characters = string.ascii_letters + string.digits + string.punctuation + ' '


class TelnetConnection(asyncio.Protocol):
    def connection_made(self, transport):
        self.peername = transport.get_extra_info('peername')
        log(f'Connection received from {self.peername}', 'CLIENT')

        self.transport = transport
        self.buffer = b''
        self.ansi_escape = b''
        self.oob = b''

        # Ask client not to local echo
        self.transport.write(bytes([Telnet.IAC, Telnet.DONT, Telnet.ECHO]))

        # Ask client not to line buffer
        self.transport.write(bytes([Telnet.IAC, Telnet.DONT, Telnet.LINEMODE]))

    def data_received(self, data):
        for byte in data:
            if byte == Telnet.IAC:   # Byte is an "Is A Command" escape byte
                if not self.oob:   # IAC received while previously being in-band
                    self.oob += bytes([Telnet.IAC])
                elif len(self.oob) == 1:   # We just switched to out-of-band (OOB) but now see it's an escaped IAC
                    # Switch back to in-band and ignore the IAC since we trash anything outside of [1,127]
                    self.oob = b''
                else:   # If we strangely receive an IAC during another OOB sequence, discard the previous OOB and restart
                    self.oob = b''
                    self.oob += bytes([Telnet.IAC])
                continue
            if self.oob:   # We are OOB and receive a byte besides IAC
                self.oob += bytes([byte])   # Buffer the byte regardless of its value
                if len(self.oob) == 3 and self.oob[1] in Telnet.IAC_VERBS:   # Standard IAC sequence
                    self.oob = b''
                elif byte == Telnet.SE:   # End of a subnegotiation sequence
                    self.oob = b''
                continue
            if 0 < byte < 128:
                if self.ansi_escape:   # We are in the middle of processing an ANSI escape sequence
                    self.ansi_escape += bytes([byte])
                    if len(self.ansi_escape) > 2 and (0x40 <= byte <= 0x7E):   # We have reached a terminating character
                        if self.ansi_escape == Ansi.LEFT_ARROW:   # Process a left arrow as a backspace
                            self.transport.write(b'\b \b')   # Send a space to make sure the wipe occurs
                            self.buffer = self.buffer[:-1]
                        elif self.ansi_escape == Ansi.HOME:   # Process a home key press as a line wipe
                            self.transport.write(b'\b' * len(self.buffer) + b' ' * len(self.buffer) + b'\b' * len(self.buffer))
                            self.buffer = b''
                        self.ansi_escape = b''   # Reset the escape sequence buffer
                elif byte == 0x1B:   # Initiate ANSI escape handling
                    self.ansi_escape = bytes([byte])
                elif byte == ord('\b'):   # Process backspace
                    self.transport.write(b'\b \b')   # Send a space to make sure the wipe occurs
                    self.buffer = self.buffer[:-1]
                elif byte == ord('\n'):   # End of a line of text
                    line = self.buffer.decode('ascii')
                    log(f"Line Received: [{line}], len={len(line)}", 'CLIENT', trivial=True)
                    self.transport.write(b'\r\n')
                    self.buffer = b''
                elif chr(byte) in bufferable_characters:   # Only record and echo what we are willing to accept
                    self.transport.write(bytes([byte]))
                    self.buffer += bytes([byte])
            else:
                pass   # Ignore null and upper-half bytes
