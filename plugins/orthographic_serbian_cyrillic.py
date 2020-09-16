# Orthographic Serbian (Cyrillic)
public_name='Orthographic Serbian (Cyrillic)'
default_data='orthographic_serbian_cyrillic.txt'
default_neighbor_lexicon='orthographic_serbian_cyrillic.txt'
default_word_lexicon='orthographic_serbian_cyrillic.txt'
default_lookup_lexicon='orthographic_serbian_cyrillic.txt'
from .subsyllabic_common import *
import plugins.orth.sr_cyrillic as language
def transform(input_sequence, frequency=1):
    return pre_transform(input_sequence, frequency=frequency, language=language)
