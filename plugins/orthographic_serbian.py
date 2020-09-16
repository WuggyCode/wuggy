# Orthographic Serbian
public_name='Orhographic Serbian'
default_data='orthographic_serbian.txt'
default_neighbor_lexicon='orthographic_serbian.txt'
default_word_lexicon='orthographic_serbian.txt'
default_lookup_lexicon='orthographic_serbian.txt'
from .subsyllabic_common import *
# TODO: ensure the right orth plugin is selected
import plugins.orth.sr as language
def transform(input_sequence, frequency=1):
    return pre_transform(input_sequence, frequency=frequency, language=language)
