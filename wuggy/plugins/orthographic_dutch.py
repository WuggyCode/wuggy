# Orthographic Dutch
# pylint: disable=unused-wildcard-import
from .orth import nl as language
from .subsyllabic_common import *
default_data = 'orthographic_dutch.txt'
default_neighbor_lexicon = 'orthographic_dutch.txt'
default_word_lexicon = 'orthographic_dutch.txt'
default_lookup_lexicon = 'orthographic_dutch.txt'


def transform(input_sequence, frequency=1):
    return pre_transform(input_sequence, frequency=frequency, language=language)
