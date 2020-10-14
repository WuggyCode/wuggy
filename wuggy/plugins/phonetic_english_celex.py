# Phonetic English
# pylint: disable=unused-wildcard-import
default_data='phonetic_english_celex.txt'
default_neighbor_lexicon='phonetic_english_celex.txt'
default_word_lexicon='phonetic_english_celex.txt'
default_lookup_lexicon='phonetic_english_celex.txt'
hidden_sequence=False
from .subsyllabic_common import *
def transform(input_sequence, frequency=1):
    return copy_onc(input_sequence, frequency=frequency)
