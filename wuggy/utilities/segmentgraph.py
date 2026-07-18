import random
from collections import defaultdict

from .positionalgraph import PositionalGraph, Vertex

__all__ = ['SegmentGraph', 'Vertex', 'CACHE_FORMAT_VERSION']

# Bump when the cached on-disk representation changes shape.
CACHE_FORMAT_VERSION = 2


class SegmentGraph(PositionalGraph):
    """
    A PositionalGraph whose symbols are linguistic segments from a language
    plugin. This layer owns everything that knows about language: parsing a
    plugin data file, filters expressed over segment fields, limit
    frequencies over named fields, and reconstructing plugin namedtuple
    segments when a cached graph is loaded. All graph mechanics — interning,
    edge arrays, masks, pruning, counting, generation — live in the kernel.
    """

    def __init__(self, language_plugin, data=None, encoding='utf-8',
                 size=100, cutoff=1, token=False):
        super().__init__()
        self.language_plugin = language_plugin
        try:
            self.hidden_sequence = self.language_plugin.hidden_sequence
        except AttributeError:
            self.hidden_sequence = False
        self.limit_frequencies = {}
        if data is not None:
            self.load(data, size=size, cutoff=cutoff, token=token)

    # The kernel stores payloads as vertex_symbols; keep the segment-named
    # accessor for callers of the pre-extraction attribute.
    @property
    def vertex_segments(self):
        return self.vertex_symbols

    def _share_domain_state(self, view):
        view.language_plugin = self.language_plugin
        view.hidden_sequence = self.hidden_sequence
        view.limit_frequencies = {}

    # ------------------------------------------------------------------
    # Construction

    def load(self, datafile, size=100, cutoff=1, token=False):
        separator = self.language_plugin.separator
        transform = self.language_plugin.transform

        def parsed_sequences():
            for line in datafile:
                fields = line.strip('\n\t').split(separator)
                reference, input_sequence, frequency = fields
                frequency = float(frequency) if token == True else 1
                sequence = transform(input_sequence, frequency)
                if frequency >= cutoff and (
                        size >= 100 or random.randint(1, 100) <= size):
                    yield sequence.representation, sequence.frequency

        self.load_sequences(parsed_sequences())
        datafile.close()

    def to_cache_state(self):
        """
        Picklable snapshot of the parsed store. Segments are flattened to
        plain tuples because plugin namedtuple classes are class attributes
        and cannot be pickled by reference.
        """
        state = {
            'version': CACHE_FORMAT_VERSION,
            'vertex_tuples': [tuple(segment)
                              for segment in self.vertex_symbols],
        }
        state.update(self._cache_arrays())
        return state

    @classmethod
    def from_cache_state(cls, language_plugin, state):
        if state.get('version') != CACHE_FORMAT_VERSION:
            raise ValueError('incompatible cache format')
        graph = cls(language_plugin)
        nfields = len(language_plugin.Segment._fields)
        segments = []
        for values in state['vertex_tuples']:
            segment_cls = (language_plugin.Segment
                           if len(values) == nfields
                           else language_plugin.SegmentH)
            segments.append(segment_cls(*values))
        graph._restore_arrays(state, segments)
        return graph

    # ------------------------------------------------------------------
    # Segment-aware filters and limits

    def segmentset_filter(self, reference_sequence, segmentset):
        segmentset = segmentset.union(set(('^', '$')))
        result = self.vertex_predicate_filter(
            lambda position, segment: segment.letters in segmentset)
        result._prune_in_place(len(reference_sequence) - 1)
        result.set_start_vertices()
        return result

    def attribute_filter(self, reference_sequence, attribute):
        nref = len(reference_sequence)
        if type(reference_sequence[0]) == self.language_plugin.Segment:
            def reference_value(position):
                return getattr(reference_sequence[position], attribute)
        else:
            def reference_value(position):
                return reference_sequence[position]
        return self.vertex_predicate_filter(
            lambda position, segment: (
                position < nref
                and getattr(segment, attribute) == reference_value(position)),
            require_dst=False)

    def build_limit_frequencies(self, fields):
        limits = defaultdict(dict)
        for key, nextkeys in self.items():
            position, value = key
            subkey_a = (position, tuple(
                getattr(value, field) for field in fields))
            for nextkey, frequency in nextkeys.items():
                position, value = nextkey
                subkey_b = (position, tuple(
                    getattr(value, field) for field in fields))
                subkey = (subkey_a, subkey_b)
                minfrequency = limits[subkey].get('min', frequency)
                limits[subkey]['min'] = min(minfrequency, frequency)
                maxfrequency = limits[subkey].get('max', frequency)
                limits[subkey]['max'] = max(maxfrequency, frequency)
        self.limit_frequencies[tuple(fields)] = limits
