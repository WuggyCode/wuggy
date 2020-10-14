# Orthographic Serbian (Latin)
# pylint: disable=unused-wildcard-import
from .orth.sr_latin import Language
from .subsyllabic_common import *
default_data = 'orthographic_serbian_latin.txt'
default_neighbor_lexicon = 'orthographic_serbian_latin.txt'
default_word_lexicon = 'orthographic_serbian_latin.txt'
default_lookup_lexicon = 'orthographic_serbian_latin.txt'


def transform(input_sequence, frequency=1):
    return pre_transform(input_sequence, frequency=frequency, language=Language())
