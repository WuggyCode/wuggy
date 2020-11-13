""".. include:: ../../documentation/baselanguageplugin/baselanguageplugin.md"""
from collections import namedtuple
from fractions import Fraction

# Pylint may report no-member error due to C extension
import Levenshtein


def compute_difference(gen_stat, ref_stat):
    if type(gen_stat) in (tuple, list):
        return [gen_stat[i] - ref_stat[i] for i in range(min(len(gen_stat), len(ref_stat)))]
    elif isinstance(gen_stat, dict):
        return dict((i, gen_stat[i] - ref_stat[i]) for i in range(len(gen_stat)))
    elif type(gen_stat) in [float, int]:
        return gen_stat - ref_stat


def compute_match(gen_stat, ref_stat):
    if gen_stat == ref_stat:
        return True
    else:
        return False


def match(function):
    function.match = compute_match
    return function


def difference(function):
    function.difference = compute_difference
    return function


class BaseLanguagePlugin():
    separator = u'\t'
    subseparator = u'|'
    default_fields = ['sequence_length']

    Sequence = namedtuple('Sequence', ['representation', 'frequency'])
    Segment = namedtuple('Segment', ('sequence_length',
                                     'segment_length', 'letters'))
    SegmentH = namedtuple('Segment', ('sequence_length',
                                      'segment_length', 'letters', 'hidden'))

    def transform(self):
        raise NotImplementedError

    def pre_transform(self, input_sequence, frequency=1, language=None):
        syllables = input_sequence.split('-')
        representation = []
        for syllable in syllables:
            try:
                segments = self.onsetnucleuscoda(syllable, language)
            except AttributeError:
                segments = (syllable, '', '')
            for segment in segments:
                representation.append(
                    (self.Segment(len(syllables), len(segment), segment)))
        representation.insert(0, (self.Segment(len(syllables), 1, '^')))
        representation.append((self.Segment(len(syllables), 1, '$')))
        return self.Sequence(tuple(representation), frequency)

    def copy_onc(self, input_sequence, frequency=1):
        representation = []
        syllables = input_sequence.split(u'-')
        nsyllables = len(syllables)
        for syllable in syllables:
            segments = syllable.split(u':')
            for segment in segments:
                representation.append(
                    (self.Segment(nsyllables, len(segment), segment)))
        representation.insert(0, (self.Segment(nsyllables, 1, '^')))
        representation.append((self.Segment(nsyllables, 1, '$')))
        return self.Sequence(tuple(representation), frequency)

    def copy_onc_hidden(self, input_sequence, frequency=1):
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
                    (self.SegmentH(nsyllables, len(segments[j]), segments[j], hidden_segments[j])))
        representation.insert(0, (self.SegmentH(nsyllables, 1, '^', '^')))
        representation.append((self.SegmentH(nsyllables, 1, '$', '$')))
        return self.Sequence(tuple(representation), frequency)

    # output modes

    def output_pass(self, sequence):
        return sequence[1::-1]

    def output_plain(self, sequence):
        return u''.join([segment.letters for segment in sequence[1:-1]])

    def output_syllabic(self, sequence):
        return '-'.join(
            u''.join(segment.letters for segment in sequence[i - 3: i])
            for i in range(4, len(sequence),
                           3))

    def output_segmental(self, sequence):
        return u':'.join([segment.letters for segment in sequence[1:-1]])

    def statistic_overlap(self, generator, generated_sequence):
        return sum([generator.reference_sequence[i] == generated_sequence[i]
                    for i in range(1, len(generator.reference_sequence) - 1)])

    def statistic_overlap_ratio(self, generator, generated_sequence):
        return Fraction(
            self.statistic_overlap(generator, generated_sequence),
            len(generator.reference_sequence) - 2)

    @match
    @difference
    def statistic_plain_length(self, generator, generated_sequence):
        return len(self.output_plain(generated_sequence)) - 2

    @match
    def statistic_lexicality(self, generator, generated_sequence):
        candidate = self.output_plain(generated_sequence)
        if candidate in generator.word_lexicon[candidate[0], len(candidate)]:
            return "W"
        else:
            return "N"

    @difference
    def _distance(self, source, target):
        return Levenshtein.distance(source, target)

    def _old(self, source, lexicon, n):
        distances = (distance for neighbor,
                     distance in self._neighbors(source, lexicon, n))
        return sum(distances) / float(n)

    def _neighbors(self, source, lexicon, n):
        neighbors = []
        for target in lexicon:
            neighbors.append((target, Levenshtein.distance(source, target)))
        neighbors.sort(key=lambda x: x[1])
        return neighbors[0:n]

    def _neighbors_at_distance(self, source, lexicon, distance):
        neighbors = []
        for target in lexicon:
            if abs(len(target) - len(source)) > distance:
                pass
            elif Levenshtein.distance(source, target) == 1:
                neighbors.append(target)
        return neighbors

    @match
    @difference
    def statistic_old20(self, generator, generated_sequence):
        return self._old(self.output_plain(generated_sequence), generator.neighbor_lexicon, 20)

    @match
    @difference
    def statistic_ned1(self, generator, generated_sequence):
        return len(self._neighbors_at_distance(
            self.output_plain(generated_sequence),
            generator.neighbor_lexicon, 1))

    @difference
    def statistic_transition_frequencies(self, generator, generated_sequence):
        return generator.bigramchain.get_frequencies(generated_sequence)

    def onsetnucleuscoda(self, orthographic_syllable, lang=None):
        self.oncpattern = lang.oncpattern
        m = self.oncpattern.match(orthographic_syllable)
        try:
            return [m.group(1), m.group(2), m.group(3)]
        except AttributeError as err:
            raise AttributeError('Input syllable could not be segmented') from err
