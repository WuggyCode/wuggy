# Orthographic Serbian (Cyrillic)
# pylint: disable=unused-wildcard-import
from .orth.sr_cyrillic import Language
from .subsyllabic_common import *
default_data = 'orthographic_serbian_cyrillic.txt'
default_neighbor_lexicon = 'orthographic_serbian_cyrillic.txt'
default_word_lexicon = 'orthographic_serbian_cyrillic.txt'
default_lookup_lexicon = 'orthographic_serbian_cyrillic.txt'


def transform(input_sequence, frequency=1):
    return pre_transform(input_sequence, frequency=frequency, language=Language())
