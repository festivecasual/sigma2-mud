import sys
from datetime import datetime


class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


def log(text, label='', trivial=False, exit_code=None):
    from world import World
    verbose_config = World().config['verbose']

    stream = sys.stdout if not exit_code else sys.stderr

    if label == '':
        label = 'LOG' if not exit_code else 'FATAL'
    if not trivial or verbose_config:
        stream.write(f"{label : <12} | {datetime.now().isoformat()} | {text}\r\n")
    if exit_code:
        sys.exit(exit_code)
