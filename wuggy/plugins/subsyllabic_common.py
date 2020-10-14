from collections import namedtuple
from fractions import Fraction
import os
import sys
# Pylint may report no-member error due to C extension
import Levenshtein
from .segment import onsetnucleuscoda, SegmentationError
from .base_plugin import difference, match, Sequence


sys.path.append(os.pardir)
separator = u'\t'
subseparator = u'|'
default_fields = ['sequence_length']
default_encoding = 'utf-8'
language = None
# TODO: already have the language files prepared
Segment = namedtuple('Segment', ('sequence_length',
                                 'segment_length', 'letters'))
SegmentH = namedtuple('Segment', ('sequence_length',
                                  'segment_length', 'letters', 'hidden'))

# TODO: move


def pre_transform(input_sequence, frequency=1, language=None):
    syllables = input_sequence.split('-')
    representation = []
    for syllable in syllables:
        try:
            segments = onsetnucleuscoda(syllable, language)
        except SegmentationError:
            segments = (syllable, '', '')
        for segment in segments:
            representation.append(
                (Segment(len(syllables), len(segment), segment)))
    representation.insert(0, (Segment(len(syllables), 1, '^')))
    representation.append((Segment(len(syllables), 1, '$')))
    return Sequence(tuple(representation), frequency)


def copy_onc(input_sequence, frequency=1):
    representation = []
    syllables = input_sequence.split(u'-')
    nsyllables = len(syllables)
    for syllable in syllables:
        segments = syllable.split(u':')
        for segment in segments:
            representation.append((Segment(nsyllables, len(segment), segment)))
    representation.insert(0, (Segment(nsyllables, 1, '^')))
    representation.append((Segment(nsyllables, 1, '$')))
    return Sequence(tuple(representation), frequency)


def copy_onc_hidden(input_sequence, frequency=1):
    representation = []
    sequence, hidden_sequence = input_sequence.split(u'|')
    syllables = sequence.split(u'-')
    hidden_syllables = hidden_sequence.split(u'-')
    nsyllables = len(syllables)
    for i in range(nsyllables):
        segments = syllables[i].split(u':')
        hidden_segments = hidden_syllables[i].split(u':')
        for j in range(len(segments)):
            representation.append(
                (SegmentH(nsyllables, len(segments[j]), segments[j], hidden_segments[j])))
    representation.insert(0, (SegmentH(nsyllables, 1, '^', '^')))
    representation.append((SegmentH(nsyllables, 1, '$', '$')))
    return Sequence(tuple(representation), frequency)

# output modes


def output_pass(sequence):
    return sequence[1::-1]


def output_plain(sequence):
    return u''.join([segment.letters for segment in sequence[1:-1]])


def output_syllabic(sequence):
    return '-'.join(u''.join(segment.letters for segment in sequence[i-3:i]) for i in range(4, len(sequence), 3))


def output_segmental(sequence):
    return u':'.join([segment.letters for segment in sequence[1:-1]])

# statistics


def statistic_overlap(generator, generated_sequence):
    """docstring for overlap"""
    return sum([generator.reference_sequence[i] == generated_sequence[i] for i in range(1, len(generator.reference_sequence)-1)])


def statistic_overlap_ratio(generator, generated_sequence):
    """docstring for overlap ratio"""
    return Fraction(statistic_overlap(generator, generated_sequence), len(generator.reference_sequence)-2)


@match
@difference
def statistic_plain_length(generator, generated_sequence):
    return len(output_plain(generated_sequence))-2


@match
def statistic_lexicality(generator, generated_sequence):
    candidate = output_plain(generated_sequence)
    if candidate in generator.word_lexicon[candidate[0], len(candidate)]:
        return "W"
    else:
        return "N"


@difference
def _distance(source, target):
    return Levenshtein.distance(source, target)


def _old(source, lexicon, n):
    distances = (distance for neighbor,
                 distance in _neighbors(source, lexicon, n))
    return sum(distances)/float(n)


def _neighbors(source, lexicon, n):
    neighbors = []
    for target in lexicon:
        neighbors.append((target, Levenshtein.distance(source, target)))
    neighbors.sort(key=lambda x: x[1])
    return neighbors[0:n]


def _neighbors_at_distance(source, lexicon, distance):
    neighbors = []
    for target in lexicon:
        if abs(len(target)-len(source)) > distance:
            pass
        elif Levenshtein.distance(source, target) == 1:
            neighbors.append(target)
    return neighbors


@match
@difference
def statistic_old20(generator, generated_sequence):
    return _old(output_plain(generated_sequence), generator.neighbor_lexicon, 20)


@match
@difference
def statistic_ned1(generator, generated_sequence):
    return len(_neighbors_at_distance(output_plain(generated_sequence), generator.neighbor_lexicon, 1))


@difference
def statistic_transition_frequencies(generator, generated_sequence):
    return generator.bigramchain.get_frequencies(generated_sequence)
