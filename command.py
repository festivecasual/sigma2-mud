from enum import Enum


class Prepositions(Enum):
    TO = "to"
    FROM = "from"
    AT = "at"
    IN = "in"
    ON = "on"


class Ordinals(Enum):
    FIRST = 1
    SECOND = 2
    THIRD = 3
    FOURTH = 4
    FIFTH = 5
    SIXTH = 6
    SEVENTH = 7
    EIGHTH = 8
    NINTH = 9
    TENTH = 10


ordinal_dict = {"1st": Ordinals.FIRST,
                "2nd": Ordinals.SECOND,
                "3rd": Ordinals.THIRD,
                "4th": Ordinals.FOURTH,
                "5th": Ordinals.FIFTH,
                "6th": Ordinals.SIXTH,
                "7th": Ordinals.SEVENTH,
                "8th": Ordinals.EIGHTH,
                "9th": Ordinals.NINTH,
                "10th": Ordinals.TENTH
                }

single_character_aliases = {
    "'": 'say',
    '"': 'say'
}


class PrepositionalPhrase(object):
    def __init__(self, preposition, obj):
        self.preposition = preposition
        self.obj = obj


class ParsedMessage(object):
    def __init__(self, verb, args, raw_text, do=None, ido=None, prepositions=None):
        self.verb = verb
        self.mapped_verb = None
        self.args = args
        self.text = raw_text
        self.direct_object = do
        self.indirect_object = ido
        self.prepositions = prepositions
        self.speaker = None


class MessageParser(object):
    def __init__(self, message):
        self.raw_message = message

    def parse(self):
        split_message = self.split_message()
        verb = split_message[0]
        args = split_message[1:]
        preps_raw = self.get_parsed_prepositional_phrases(args)
        return ParsedMessage(verb, args, self.raw_message, None, None, preps_raw)

    def split_message(self):
        message = self.raw_message
        if self.raw_message and self.raw_message[0] in single_character_aliases:
            verb = single_character_aliases[self.raw_message[0]]
            message = f'{verb} {self.raw_message[1:]}'
        return message.split(" ")

    @staticmethod
    def get_parsed_prepositional_phrases(split_message):
        phrases = []
        preposition_indexes = []
        for idx in range(len(split_message)):
            if split_message[idx] in (prep.value for prep in Prepositions):
                preposition_indexes.append(idx)
        while preposition_indexes:
            idx = preposition_indexes.pop(0)
            if preposition_indexes:
                idx2 = preposition_indexes[0]
            else:
                idx2 = len(split_message)
            phrases.append(split_message[idx:idx2])
        return phrases


def process_command(parsed_message, register):
    if parsed_message.verb == '':
        return False
    for i in sorted(register.keys()):
        for register_item in register[i]:
            if register_item[0].startswith(parsed_message.verb):
                parsed_message.mapped_verb = register_item[0]
                return register_item[1](parsed_message)
    return False
