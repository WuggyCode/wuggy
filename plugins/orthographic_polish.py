# -*- encoding: utf-8 -*-
# Subsyllabic Polish
# by Paweł Mandera
# pawel.mandera@ugent.be
public_name='Orthographic Polish'
default_data='orthographic_polish.txt'
default_neighbor_lexicon='orthographic_polish.txt'
default_word_lexicon='orthographic_polish.txt'
default_lookup_lexicon='orthographic_polish.txt'
from .subsyllabic_common import *
import plugins.orth.pl as language
def transform(input_sequence, frequency=1):
    return pre_transform(input_sequence, frequency=frequency, language=language)
