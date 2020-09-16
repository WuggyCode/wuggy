# Orthographic Italian
public_name='Orthographic Italian'
default_data='orthographic_italian.txt'
default_neighbor_lexicon='orthographic_italian.txt'
default_word_lexicon='orthographic_italian.txt'
default_lookup_lexicon='orthographic_italian.txt'
from .subsyllabic_common import *
import plugins.orth.it as language
def transform(input_sequence, frequency=1):
    return pre_transform(input_sequence, frequency=frequency, language=language)
