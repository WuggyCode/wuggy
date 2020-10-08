# Orthographic Spanish
# pylint: disable=unused-wildcard-import
default_data='orthographic_spanish.txt'
default_neighbor_lexicon='orthographic_spanish.txt'
default_word_lexicon='orthographic_spanish.txt'
default_lookup_lexicon='orthographic_spanish.txt'
from .subsyllabic_common import *
import plugins.orth.es as language
def transform(input_sequence, frequency=1):
    return pre_transform(input_sequence, frequency=frequency, language=language)
