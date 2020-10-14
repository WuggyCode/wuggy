# Orthographic Vietnamese
# pylint: disable=unused-wildcard-import
from .orth import vi as language
from .subsyllabic_common import *
default_data = 'orthographic_vietnamese.txt'
default_neighbor_lexicon = 'orthographic_vietnamese.txt'
default_word_lexicon = 'orthographic_vietnamese.txt'
default_lookup_lexicon = 'orthographic_vietnamese.txt'


def transform(input_sequence, frequency=1):
    return pre_transform(input_sequence, frequency=frequency, language=language)
