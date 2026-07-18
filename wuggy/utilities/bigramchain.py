import random
from collections import defaultdict, namedtuple

import numpy as np

Link = namedtuple('Link', ['position', 'value'])

_SENTINEL = object()

# Bump when the cached on-disk representation changes shape.
CACHE_FORMAT_VERSION = 1


class BigramChain:
    """
    A layered DAG over (position, segment) nodes storing the next possible
    values, given a list of input sequences.

    Nodes are interned to integer ids; edges live in flat NumPy arrays
    (source, destination, frequency) sorted by source position. Filters
    return lightweight views that share the node/edge store and differ only
    in their boolean edge mask, so no filter ever copies the chain.
    """

    def __init__(self, language_plugin, data=None, encoding='utf-8',
                 size=100, cutoff=1, token=False):
        self.language_plugin = language_plugin
        try:
            self.hidden_sequence = self.language_plugin.hidden_sequence
        except AttributeError:
            self.hidden_sequence = False
        self.startkeys = {}
        self.limit_frequencies = {}
        # Shared node/edge store; populated by load() or shared by views.
        self.node_segments = []
        self.node_positions = np.empty(0, dtype=np.int32)
        self.node_index = {}
        self.edge_src = np.empty(0, dtype=np.int32)
        self.edge_dst = np.empty(0, dtype=np.int32)
        self.edge_freq = np.empty(0, dtype=np.float64)
        self.edge_pos = np.empty(0, dtype=np.int32)
        self._position_slices = {}
        self.edge_mask = np.empty(0, dtype=bool)
        self._edge_lookup = None
        self._out_edges = None
        if data is not None:
            self.load(data, size=size, cutoff=cutoff, token=token)

    # ------------------------------------------------------------------
    # Construction

    def load(self, datafile, size=100, cutoff=1, token=False):
        node_index = {}
        node_segments = []
        node_positions = []
        edge_weights = {}
        separator = self.language_plugin.separator
        transform = self.language_plugin.transform

        def intern(position, segment):
            key = (position, segment)
            node_id = node_index.get(key)
            if node_id is None:
                node_id = len(node_segments)
                node_index[key] = node_id
                node_segments.append(segment)
                node_positions.append(position)
            return node_id

        for line in datafile:
            fields = line.strip('\n\t').split(separator)
            reference, input_sequence, frequency = fields
            frequency = float(frequency) if token == True else 1
            sequence = transform(input_sequence, frequency)
            representation = sequence.representation
            n = len(representation)
            if frequency >= cutoff and (
                    size >= 100 or random.randint(1, 100) <= size):
                previous = intern(0, representation[0])
                for j in range(1, n):
                    current = intern(j, representation[j])
                    edge = (previous, current)
                    edge_weights[edge] = edge_weights.get(
                        edge, 0) + sequence.frequency
                    previous = current
        datafile.close()

        self.node_index = node_index
        self.node_segments = node_segments
        self.node_positions = np.array(node_positions, dtype=np.int32)
        nedges = len(edge_weights)
        src = np.empty(nedges, dtype=np.int32)
        dst = np.empty(nedges, dtype=np.int32)
        freq = np.empty(nedges, dtype=np.float64)
        for i, ((s, d), f) in enumerate(edge_weights.items()):
            src[i] = s
            dst[i] = d
            freq[i] = f
        # Sort edges by source position so clean() can sweep positions
        # back-to-front over contiguous slices.
        pos = self.node_positions[src] if nedges else np.empty(0, np.int32)
        order = np.argsort(pos, kind='stable')
        self.edge_src = src[order]
        self.edge_dst = dst[order]
        self.edge_freq = freq[order]
        self.edge_pos = pos[order]
        self._build_position_slices()
        self.edge_mask = np.ones(nedges, dtype=bool)
        self._invalidate_caches()
        self.set_startkeys()

    def to_cache_state(self):
        """
        Picklable snapshot of the parsed store. Segments are flattened to
        plain tuples because plugin namedtuple classes are class attributes
        and cannot be pickled by reference.
        """
        return {
            'version': CACHE_FORMAT_VERSION,
            'node_tuples': [tuple(segment) for segment in self.node_segments],
            'node_positions': self.node_positions,
            'edge_src': self.edge_src,
            'edge_dst': self.edge_dst,
            'edge_freq': self.edge_freq,
            'edge_pos': self.edge_pos,
        }

    @classmethod
    def from_cache_state(cls, language_plugin, state):
        if state.get('version') != CACHE_FORMAT_VERSION:
            raise ValueError('incompatible cache format')
        chain = cls(language_plugin)
        nfields = len(language_plugin.Segment._fields)
        segments = []
        for values in state['node_tuples']:
            segment_cls = (language_plugin.Segment
                           if len(values) == nfields
                           else language_plugin.SegmentH)
            segments.append(segment_cls(*values))
        chain.node_segments = segments
        chain.node_positions = state['node_positions']
        chain.node_index = {
            (int(position), segment): node_id
            for node_id, (position, segment)
            in enumerate(zip(chain.node_positions, segments))}
        chain.edge_src = state['edge_src']
        chain.edge_dst = state['edge_dst']
        chain.edge_freq = state['edge_freq']
        chain.edge_pos = state['edge_pos']
        chain._build_position_slices()
        chain.edge_mask = np.ones(len(chain.edge_src), dtype=bool)
        chain._invalidate_caches()
        chain.set_startkeys()
        return chain

    def _build_position_slices(self):
        self._position_slices = {}
        if len(self.edge_pos) == 0:
            return
        positions = np.unique(self.edge_pos)
        starts = np.searchsorted(self.edge_pos, positions, side='left')
        ends = np.searchsorted(self.edge_pos, positions, side='right')
        for position, start, end in zip(positions, starts, ends):
            self._position_slices[int(position)] = slice(int(start), int(end))

    def _view(self, edge_mask):
        """A chain sharing this chain's store with a different edge mask."""
        view = BigramChain.__new__(BigramChain)
        view.language_plugin = self.language_plugin
        view.hidden_sequence = self.hidden_sequence
        view.startkeys = {}
        view.limit_frequencies = {}
        view.node_segments = self.node_segments
        view.node_positions = self.node_positions
        view.node_index = self.node_index
        view.edge_src = self.edge_src
        view.edge_dst = self.edge_dst
        view.edge_freq = self.edge_freq
        view.edge_pos = self.edge_pos
        view._position_slices = self._position_slices
        view.edge_mask = edge_mask
        view._invalidate_caches()
        return view

    def _invalidate_caches(self):
        self._edge_lookup = None
        self._out_edges = None

    # ------------------------------------------------------------------
    # Derived structures (cached per view)

    def _edges(self):
        """{(src_id, dst_id): frequency} over active edges."""
        if self._edge_lookup is None:
            active = np.flatnonzero(self.edge_mask)
            self._edge_lookup = {
                (int(self.edge_src[i]), int(self.edge_dst[i])):
                    float(self.edge_freq[i])
                for i in active}
        return self._edge_lookup

    def _adjacency(self):
        """{src_id: [dst_id, ...]} over active edges."""
        if self._out_edges is None:
            adjacency = defaultdict(list)
            for i in np.flatnonzero(self.edge_mask):
                adjacency[int(self.edge_src[i])].append(int(self.edge_dst[i]))
            self._out_edges = dict(adjacency)
        return self._out_edges

    def _node_id(self, position, segment):
        return self.node_index.get((position, segment))

    # ------------------------------------------------------------------
    # Mapping-style compatibility (cold paths: display, dumps, limits)

    def __len__(self):
        return len(self._adjacency())

    def __contains__(self, key):
        node_id = self._node_id(key.position, key.value)
        return node_id is not None and node_id in self._adjacency()

    def keys(self):
        return [Link(int(self.node_positions[node_id]),
                     self.node_segments[node_id])
                for node_id in self._adjacency()]

    def items(self):
        for node_id, children in self._adjacency().items():
            key = Link(int(self.node_positions[node_id]),
                       self.node_segments[node_id])
            edges = self._edges()
            nextkeys = {
                Link(int(self.node_positions[child]),
                     self.node_segments[child]):
                    edges[(node_id, child)]
                for child in children}
            yield key, nextkeys

    # ------------------------------------------------------------------
    # Public interface

    def set_startkeys(self, reference_sequence=None, fields=None):
        if fields is None:
            fields = self.language_plugin.default_fields
        adjacency = self._adjacency()
        self.startkeys = {
            Link(0, self.node_segments[node_id]): 0
            for node_id in adjacency
            if self.node_positions[node_id] == 0}

    def get_frequencies(self, reference_sequence):
        frequencies = {}
        edges = self._edges()
        for position in range(len(reference_sequence) - 1):
            source = self._node_id(position, reference_sequence[position])
            target = self._node_id(
                position + 1, reference_sequence[position + 1])
            if source is None or target is None:
                frequencies[position] = 0
            else:
                frequencies[position] = edges.get((source, target), 0)
        return frequencies

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

    def frequency_filter(self, reference_sequence, lower, upper, kind='dev'):
        # Concentric search widens bands as 2**k without bound; clamp so the
        # arbitrary-precision ints survive the conversion to float64.
        lower = float(max(min(lower, 1e300), -1e300))
        upper = float(max(min(upper, 1e300), -1e300))
        nref = len(reference_sequence)
        max_position = int(self.edge_pos[-1]) if len(self.edge_pos) else -1
        lower_by_position = np.full(max_position + 2, np.inf)
        upper_by_position = np.full(max_position + 2, -np.inf)
        if kind == 'dev':
            frequencies = self.get_frequencies(reference_sequence)
            for position, frequency in frequencies.items():
                if position <= max_position:
                    lower_by_position[position] = frequency - lower
                    upper_by_position[position] = frequency + upper
        elif kind == 'limit':
            limit = min(nref - 1, max_position + 1)
            lower_by_position[:limit] = lower
            upper_by_position[:limit] = upper
        if len(self.edge_pos):
            edge_lower = lower_by_position[self.edge_pos]
            edge_upper = upper_by_position[self.edge_pos]
            mask = (self.edge_mask
                    & (self.edge_freq >= edge_lower)
                    & (self.edge_freq <= edge_upper))
        else:
            mask = self.edge_mask.copy()
        result = self._view(mask)._clean_in_place(nref - 1)
        result.set_startkeys()
        return result

    def segmentset_filter(self, reference_sequence, segmentset):
        segmentset = segmentset.union(set(('^', '$')))
        node_pass = np.fromiter(
            (segment.letters in segmentset for segment in self.node_segments),
            dtype=bool, count=len(self.node_segments))
        if len(self.edge_mask):
            mask = (self.edge_mask
                    & node_pass[self.edge_src] & node_pass[self.edge_dst])
        else:
            mask = self.edge_mask.copy()
        result = self._view(mask)._clean_in_place(len(reference_sequence) - 1)
        result.set_startkeys()
        return result

    def attribute_filter(self, reference_sequence, attribute):
        nref = len(reference_sequence)
        if type(reference_sequence[0]) == self.language_plugin.Segment:
            def reference_value(position):
                return getattr(reference_sequence[position], attribute)
        else:
            def reference_value(position):
                return reference_sequence[position]
        node_pass = np.zeros(len(self.node_segments), dtype=bool)
        for node_id, segment in enumerate(self.node_segments):
            position = int(self.node_positions[node_id])
            if position < nref:
                node_pass[node_id] = (
                    getattr(segment, attribute) == reference_value(position))
        if len(self.edge_mask):
            mask = self.edge_mask & node_pass[self.edge_src]
        else:
            mask = self.edge_mask.copy()
        return self._view(mask)

    def clean(self, maxpos):
        """
        Remove chains that can not be completed.
        """
        return self._view(self.edge_mask.copy())._clean_in_place(maxpos)

    def _clean_in_place(self, maxpos):
        """
        Keep only edges on a path reaching position maxpos: one backward
        sweep over positions instead of the old copy-until-fixpoint pass.
        An edge survives if its destination is at maxpos or its destination
        has a surviving outgoing edge.
        """
        mask = self.edge_mask
        if len(mask) == 0:
            return self
        mask[self.edge_pos >= maxpos] = False
        alive = self.node_positions == maxpos
        for position in range(maxpos - 1, -1, -1):
            edge_slice = self._position_slices.get(position)
            if edge_slice is None:
                continue
            keep = mask[edge_slice] & alive[self.edge_dst[edge_slice]]
            mask[edge_slice] = keep
            alive[self.edge_src[edge_slice][keep]] = True
        self._invalidate_caches()
        return self

    def generate(self, startkeys=None):
        if startkeys is None:
            startkeys = self.startkeys
        if len(self) == 0:
            raise Exception('LinkError')
        adjacency = self._adjacency()
        segments = self.node_segments

        starts = []
        for key in startkeys:
            node_id = self._node_id(key.position, key.value)
            if node_id is not None and node_id in adjacency:
                starts.append((key.value, node_id))
            else:
                starts.append((key.value, None))
        random.shuffle(starts)

        for start_value, start_id in starts:
            if start_id is None:
                yield (start_value,)
                continue
            path = [start_id]
            children = adjacency[start_id][:]
            random.shuffle(children)
            stack = [iter(children)]
            while stack:
                node_id = next(stack[-1], _SENTINEL)
                if node_id is _SENTINEL:
                    stack.pop()
                    path.pop()
                    continue
                children = adjacency.get(node_id)
                if children:
                    path.append(node_id)
                    children = children[:]
                    random.shuffle(children)
                    stack.append(iter(children))
                else:
                    yield tuple(segments[i] for i in path) + (
                        segments[node_id],)

    def display(self):
        for key, nextkeys in sorted(self.items(), key=lambda x: x):
            print('***', key.position, key.value)
            for nextkey, frequency in nextkeys.items():
                print(nextkey.value, frequency)
