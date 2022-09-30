import enum
import glob
import importlib
import os
import sys
import types

from collections import defaultdict
from command import Prepositions

DEFAULT_PRIORITY = 3


class RegistrationError(Exception):
    pass


class MissingAliasError(Exception):
    pass


class CommandStatus(enum.Enum):
    SUCCESS = 0
    FAILURE = 1


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


class Alias(Command):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if kwargs.get('target') is None:
            raise MissingAliasError(f'Alias {self.__name__} does not define an alias target')

        self.target_name = kwargs['target']
        self.target = None

    def __call__(self, *args, **kwargs):
        if not self.function and isinstance(args[0], types.FunctionType):
            self.function = args[0]
            return self
        if self.target is not None:
            res = self.target(*args, **kwargs)
            if res == CommandStatus.SUCCESS:
                self.function(*args, **kwargs) #TODO: need to rework slightly. Technically function could fail.
            return res

    def link_target(self, registry):
        if self.target is not None:
            #TODO add logging
            return
        for i in sorted(registry.keys()):
            for register_item in registry[i]:
                if self.target_name == register_item[0]:
                    self.target = register_item[1]
                    break


def register_commands():
    module_names = glob.glob(os.path.join(sigma_path(), "commands", '*.py'))
    registry = defaultdict(lambda: [])
    aliases = []
    for name in module_names:
        module_name = convert_name(name)
        module = importlib.import_module(module_name)
        for fn in dir(module):
            if isinstance(getattr(module, fn), Command):
                registry[getattr(module, fn).priority].append((fn, getattr(module, fn),))
            if isinstance(getattr(module, fn), Alias):
                aliases.append(getattr(module, fn))

    for entry in registry:
        registry[entry].sort(key=lambda x: x[0])
        pass

    for alias in aliases:
        alias.link_target(registry)

    return registry


def convert_name(module_name):
    if module_name.startswith(sigma_path()):
        module_name = module_name[len(sigma_path()) + 1:]  # include the beginning slash
    module_name = module_name.replace('/', '.')
    return module_name[0:module_name.find('.py')] if module_name.find('.py') != 1 else module_name


def sigma_path():
    sigma_command = os.path.dirname(sys.argv[0])
    return os.path.abspath(sigma_command)
