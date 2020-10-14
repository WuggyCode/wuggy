# Phonetic Italian
# pylint: disable=unused-wildcard-import
from .phon.it import Language
from .subsyllabic_common import *
default_data = 'phonetic_italian.txt'
default_neighbor_lexicon = 'phonetic_italian.txt'
default_word_lexicon = 'phonetic_italian.txt'
default_lookup_lexicon = 'phonetic_italian.txt'


def transform(input_sequence, frequency=1):
    return pre_transform(input_sequence, frequency=frequency, language=Language())
