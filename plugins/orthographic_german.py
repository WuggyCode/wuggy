# Orthographic German
public_name='Orthographic German'
default_data='orthographic_german.txt'
default_neighbor_lexicon='orthographic_german.txt'
default_word_lexicon='orthographic_german.txt'
default_lookup_lexicon='orthographic_german.txt'
from .subsyllabic_common import *
import plugins.orth.de as language
def transform(input_sequence, frequency=1):
    return pre_transform(input_sequence, frequency=frequency, language=language)
