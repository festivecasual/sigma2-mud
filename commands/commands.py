import glob
import importlib
import os
import sys
import types

from collections import defaultdict
from command import Prepositions

DEFAULT_PRIORITY = 3


class Alias(object):
    def __init__(self, alias=None, priority=DEFAULT_PRIORITY):
        self.alias = alias
        self.priority = DEFAULT_PRIORITY

    def __call__(self, fn, *args, **kwargs):
        fn()
        # TODO: Add Alias Call


class Command(object):
    def __init__(self, *args, **kwargs):
        self.function = None
        if len(args) == 0:
            self.priority = kwargs.get('priority', DEFAULT_PRIORITY)
        else:
            self.priority = DEFAULT_PRIORITY
            self.function = args[0]

    def __call__(self,  *args, **kwargs):
        if not self.function and isinstance(args[0], types.FunctionType):
            self.function = args[0]
            return self
        return self.function(*args, **kwargs)


def register_commands():
    module_names = glob.glob(os.path.join(sigma_path(), "commands", '*.py'))
    registry = defaultdict(lambda: [])
    for name in module_names:
        module_name = convert_name(name)
        module = importlib.import_module(module_name)
        for fn in dir(module):
            if type(getattr(module, fn)) in (Alias, Command,):
                registry[getattr(module, fn).priority].append((fn, getattr(module, fn),))
    # TODO: sort the registry alphabetically

    return registry


def convert_name(module_name):
    if module_name.startswith(sigma_path()):
        module_name=module_name[len(sigma_path()) + 1:] # include the beginning slash
    module_name = module_name.replace('/', '.')
    return module_name[0:module_name.find('.py')] if module_name.find('.py') != 1 else module_name


def sigma_path():
    sigma_command = os.path.dirname(sys.argv[0])
    return os.path.abspath(sigma_command)
