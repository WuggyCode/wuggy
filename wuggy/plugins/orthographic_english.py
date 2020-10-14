# Orthographic English
# pylint: disable=unused-wildcard-import
from .orth.en import Language
from .subsyllabic_common import *
default_data = 'orthographic_english.txt'
default_neighbor_lexicon = 'orthographic_english.txt'
default_word_lexicon = 'orthographic_english.txt'
default_lookup_lexicon = 'orthographic_english.txt'


def transform(input_sequence, frequency=1):
    return pre_transform(input_sequence, frequency=frequency, language=Language())
