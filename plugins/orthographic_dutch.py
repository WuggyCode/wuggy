# Orthographic Dutch
public_name='Orthographic Dutch'
default_data='orthographic_dutch.txt'
default_neighbor_lexicon='orthographic_dutch.txt'
default_word_lexicon='orthographic_dutch.txt'
default_lookup_lexicon='orthographic_dutch.txt'
from .subsyllabic_common import *
import plugins.orth.nl as language
def transform(input_sequence, frequency=1):
    return pre_transform(input_sequence, frequency=frequency, language=language)
