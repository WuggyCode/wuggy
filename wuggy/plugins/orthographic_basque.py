# Orthographic Basque
# pylint: disable=unused-wildcard-import
from .orth import es as language
from .subsyllabic_common import *
default_data = 'orthographic_basque.txt'
default_neighbor_lexicon = 'orthographic_basque.txt'
default_word_lexicon = 'orthographic_basque.txt'
default_lookup_lexicon = 'orthographic_basque.txt'


def transform(input_sequence, frequency=1):
    return pre_transform(input_sequence, frequency=frequency, language=language)
