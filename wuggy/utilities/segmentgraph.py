import random
from collections import defaultdict, namedtuple

import numpy as np

Vertex = namedtuple('Vertex', ['position', 'value'])

_SENTINEL = object()

# Bump when the cached on-disk representation changes shape.
CACHE_FORMAT_VERSION = 2


class SegmentGraph:
    """
    A layered DAG over (position, segment) vertices storing the next possible
    values, given a list of input sequences.

    Nodes are interned to integer ids; edges live in flat NumPy arrays
    (source, destination, frequency) sorted by source position. Filters
    return lightweight views that share the vertex/edge store and differ only
    in their boolean edge mask, so no filter ever copies the graph.
    """

    def __init__(self, language_plugin, data=None, encoding='utf-8',
                 size=100, cutoff=1, token=False):
        self.language_plugin = language_plugin
        try:
            self.hidden_sequence = self.language_plugin.hidden_sequence
        except AttributeError:
            self.hidden_sequence = False
        self.start_vertices = {}
        self.limit_frequencies = {}
        # Shared vertex/edge store; populated by load() or shared by views.
        self.vertex_segments = []
        self.vertex_positions = np.empty(0, dtype=np.int32)
        self.vertex_index = {}
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
        vertex_index = {}
        vertex_segments = []
        vertex_positions = []
        edge_weights = {}
        separator = self.language_plugin.separator
        transform = self.language_plugin.transform

        def intern(position, segment):
            key = (position, segment)
            vertex_id = vertex_index.get(key)
            if vertex_id is None:
                vertex_id = len(vertex_segments)
                vertex_index[key] = vertex_id
                vertex_segments.append(segment)
                vertex_positions.append(position)
            return vertex_id

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

        self.vertex_index = vertex_index
        self.vertex_segments = vertex_segments
        self.vertex_positions = np.array(vertex_positions, dtype=np.int32)
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
        pos = self.vertex_positions[src] if nedges else np.empty(0, np.int32)
        order = np.argsort(pos, kind='stable')
        self.edge_src = src[order]
        self.edge_dst = dst[order]
        self.edge_freq = freq[order]
        self.edge_pos = pos[order]
        self._build_position_slices()
        self.edge_mask = np.ones(nedges, dtype=bool)
        self._invalidate_caches()
        self.set_start_vertices()

    def to_cache_state(self):
        """
        Picklable snapshot of the parsed store. Segments are flattened to
        plain tuples because plugin namedtuple classes are class attributes
        and cannot be pickled by reference.
        """
        return {
            'version': CACHE_FORMAT_VERSION,
            'vertex_tuples': [tuple(segment) for segment in self.vertex_segments],
            'vertex_positions': self.vertex_positions,
            'edge_src': self.edge_src,
            'edge_dst': self.edge_dst,
            'edge_freq': self.edge_freq,
            'edge_pos': self.edge_pos,
        }

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
        graph.vertex_segments = segments
        graph.vertex_positions = state['vertex_positions']
        graph.vertex_index = {
            (int(position), segment): vertex_id
            for vertex_id, (position, segment)
            in enumerate(zip(graph.vertex_positions, segments))}
        graph.edge_src = state['edge_src']
        graph.edge_dst = state['edge_dst']
        graph.edge_freq = state['edge_freq']
        graph.edge_pos = state['edge_pos']
        graph._build_position_slices()
        graph.edge_mask = np.ones(len(graph.edge_src), dtype=bool)
        graph._invalidate_caches()
        graph.set_start_vertices()
        return graph

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
        """A graph sharing this graph's store with a different edge mask."""
        view = SegmentGraph.__new__(SegmentGraph)
        view.language_plugin = self.language_plugin
        view.hidden_sequence = self.hidden_sequence
        view.start_vertices = {}
        view.limit_frequencies = {}
        view.vertex_segments = self.vertex_segments
        view.vertex_positions = self.vertex_positions
        view.vertex_index = self.vertex_index
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

    def _vertex_id(self, position, segment):
        return self.vertex_index.get((position, segment))

    # ------------------------------------------------------------------
    # Mapping-style compatibility (cold paths: display, dumps, limits)

    def __len__(self):
        return len(self._adjacency())

    def __contains__(self, key):
        vertex_id = self._vertex_id(key.position, key.value)
        return vertex_id is not None and vertex_id in self._adjacency()

    def keys(self):
        return [Vertex(int(self.vertex_positions[vertex_id]),
                     self.vertex_segments[vertex_id])
                for vertex_id in self._adjacency()]

    def items(self):
        for vertex_id, children in self._adjacency().items():
            key = Vertex(int(self.vertex_positions[vertex_id]),
                       self.vertex_segments[vertex_id])
            edges = self._edges()
            nextkeys = {
                Vertex(int(self.vertex_positions[child]),
                     self.vertex_segments[child]):
                    edges[(vertex_id, child)]
                for child in children}
            yield key, nextkeys

    # ------------------------------------------------------------------
    # Public interface

    def set_start_vertices(self, reference_sequence=None, fields=None):
        if fields is None:
            fields = self.language_plugin.default_fields
        adjacency = self._adjacency()
        self.start_vertices = {
            Vertex(0, self.vertex_segments[vertex_id]): 0
            for vertex_id in adjacency
            if self.vertex_positions[vertex_id] == 0}

    def get_frequencies(self, reference_sequence):
        frequencies = {}
        edges = self._edges()
        for position in range(len(reference_sequence) - 1):
            source = self._vertex_id(position, reference_sequence[position])
            target = self._vertex_id(
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
        result = self._view(mask)._prune_in_place(nref - 1)
        result.set_start_vertices()
        return result

    def segmentset_filter(self, reference_sequence, segmentset):
        segmentset = segmentset.union(set(('^', '$')))
        vertex_pass = np.fromiter(
            (segment.letters in segmentset for segment in self.vertex_segments),
            dtype=bool, count=len(self.vertex_segments))
        if len(self.edge_mask):
            mask = (self.edge_mask
                    & vertex_pass[self.edge_src] & vertex_pass[self.edge_dst])
        else:
            mask = self.edge_mask.copy()
        result = self._view(mask)._prune_in_place(len(reference_sequence) - 1)
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
        vertex_pass = np.zeros(len(self.vertex_segments), dtype=bool)
        for vertex_id, segment in enumerate(self.vertex_segments):
            position = int(self.vertex_positions[vertex_id])
            if position < nref:
                vertex_pass[vertex_id] = (
                    getattr(segment, attribute) == reference_value(position))
        if len(self.edge_mask):
            mask = self.edge_mask & vertex_pass[self.edge_src]
        else:
            mask = self.edge_mask.copy()
        return self._view(mask)

    def prune(self, maxpos):
        """
        Remove paths that can not be completed.
        """
        return self._view(self.edge_mask.copy())._prune_in_place(maxpos)

    def _prune_in_place(self, maxpos):
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
        alive = self.vertex_positions == maxpos
        for position in range(maxpos - 1, -1, -1):
            edge_slice = self._position_slices.get(position)
            if edge_slice is None:
                continue
            keep = mask[edge_slice] & alive[self.edge_dst[edge_slice]]
            mask[edge_slice] = keep
            alive[self.edge_src[edge_slice][keep]] = True
        self._invalidate_caches()
        return self

    def _resolve_start_vertices(self, start_vertices, adjacency):
        """[(segment value, vertex id or None if not in the graph), ...]"""
        starts = []
        for key in start_vertices:
            vertex_id = self._vertex_id(key.position, key.value)
            if vertex_id is not None and vertex_id in adjacency:
                starts.append((key.value, vertex_id))
            else:
                starts.append((key.value, None))
        return starts

    def _completion_counts(self, weighted=False):
        """
        Per-vertex number of complete paths (or, when weighted, total path
        weight as the product of edge frequencies) from the vertex to any
        terminal vertex, over active edges. A vertex with no active outgoing
        edges is a terminal and counts as one path of weight 1, matching
        generate()'s yield condition.
        """
        adjacency = self._adjacency()
        vertices = set(adjacency)
        for children in adjacency.values():
            vertices.update(children)
        edges = self._edges() if weighted else None
        counts = {}
        for vertex in sorted(
                vertices, key=lambda n: int(self.vertex_positions[n]),
                reverse=True):
            children = adjacency.get(vertex)
            if not children:
                counts[vertex] = 1.0 if weighted else 1
            elif weighted:
                counts[vertex] = sum(
                    edges[(vertex, child)] * counts[child]
                    for child in children)
            else:
                counts[vertex] = sum(counts[child] for child in children)
        return counts

    def count_paths(self, start_vertices=None):
        """
        Exact number of sequences generate() would yield, without
        generating them. Start vertices that are not part of the graph yield a
        single one-segment sequence and therefore count as one path.
        """
        if start_vertices is None:
            start_vertices = self.start_vertices
        counts = self._completion_counts()
        total = 0
        for _, vertex_id in self._resolve_start_vertices(start_vertices,
                                                  self._adjacency()):
            total += 1 if vertex_id is None else counts[vertex_id]
        return total

    def generate(self, start_vertices=None, mode='exhaustive', rng=random):
        """
        Yield complete segment sequences from the (filtered) graph.

        Modes:
            'exhaustive' — depth-first traversal with shuffled edge order
                (the classic behavior). Complete, but sequence order is
                biased toward low-branching regions of the graph.
            'uniform'    — every sequence exactly once, in unbiased random
                order (uniform sampling without replacement).
            'weighted'   — every sequence exactly once, sampled without
                replacement with probability proportional to the product
                of its transition frequencies, so the most word-like
                sequences tend to arrive first.
        """
        if mode == 'uniform':
            return self._generate_sampled(start_vertices, weighted=False, rng=rng)
        if mode == 'weighted':
            return self._generate_sampled(start_vertices, weighted=True, rng=rng)
        if mode != 'exhaustive':
            raise ValueError(f"Unknown generation mode {mode!r}")
        return self._generate_exhaustive(start_vertices, rng)

    def _generate_exhaustive(self, start_vertices, rng):
        if start_vertices is None:
            start_vertices = self.start_vertices
        if len(self) == 0:
            raise Exception('EmptyGraphError')
        adjacency = self._adjacency()
        segments = self.vertex_segments

        starts = self._resolve_start_vertices(start_vertices, adjacency)
        rng.shuffle(starts)

        for start_value, start_id in starts:
            if start_id is None:
                yield (start_value,)
                continue
            path = [start_id]
            children = adjacency[start_id][:]
            rng.shuffle(children)
            stack = [iter(children)]
            while stack:
                vertex_id = next(stack[-1], _SENTINEL)
                if vertex_id is _SENTINEL:
                    stack.pop()
                    path.pop()
                    continue
                children = adjacency.get(vertex_id)
                if children:
                    path.append(vertex_id)
                    children = children[:]
                    rng.shuffle(children)
                    stack.append(iter(children))
                else:
                    yield tuple(segments[i] for i in path) + (
                        segments[vertex_id],)

    def _generate_sampled(self, start_vertices, weighted, rng):
        """
        Sampling without replacement over complete paths.

        The completion counts/weights below a vertex are shared by every
        prefix that reaches it, so a drawn path must only be removed for
        its own prefix. Removed paths are therefore tracked in a prefix
        trie: during a draw, the available mass under child c is the
        vertex's total (count or weight) minus what the trie records as
        already drawn through this exact prefix. Integer counts guarantee
        each path is yielded exactly once and the generator terminates;
        float weights only bias the selection order in weighted mode.
        Memory grows with the number of sequences drawn (one trie chain
        per draw); use exhaustive mode for memory-free full drains.
        """
        if start_vertices is None:
            start_vertices = self.start_vertices
        if len(self) == 0:
            raise Exception('EmptyGraphError')
        adjacency = self._adjacency()
        segments = self.vertex_segments
        edges = self._edges()
        counts = self._completion_counts()
        weights = self._completion_counts(weighted=True) if weighted else None

        starts = self._resolve_start_vertices(start_vertices, adjacency)
        # Trie vertex: [removed_count, removed_weight, children_by_dag_vertex].
        trie_root = [0, 0.0, {}]
        singletons_drawn = set()

        def available(trie_children, vertex_id):
            removed = trie_children.get(vertex_id)
            return counts[vertex_id] - (removed[0] if removed else 0)

        while True:
            root_children = trie_root[2]
            live = []
            for index, (value, vertex_id) in enumerate(starts):
                if vertex_id is None:
                    if index not in singletons_drawn:
                        live.append((index, value, None, 1, 1.0))
                else:
                    avail = available(root_children, vertex_id)
                    if avail > 0:
                        removed = root_children.get(vertex_id)
                        mass = ((weights[vertex_id]
                                 - (removed[1] if removed else 0.0))
                                if weighted else float(avail))
                        live.append((index, value, vertex_id, avail, mass))
            if not live:
                return

            if weighted:
                total_mass = sum(entry[4] for entry in live)
                pick = rng.random() * max(total_mass, 0.0)
                chosen = live[-1]
                for entry in live:
                    pick -= entry[4]
                    if pick <= 0:
                        chosen = entry
                        break
            else:
                pick = rng.randrange(sum(entry[3] for entry in live))
                chosen = live[-1]
                for entry in live:
                    pick -= entry[3]
                    if pick < 0:
                        chosen = entry
                        break
            index, value, vertex_id = chosen[0], chosen[1], chosen[2]
            if vertex_id is None:
                singletons_drawn.add(index)
                yield (value,)
                continue

            path = [vertex_id]
            current = vertex_id
            trie_cursor = trie_root[2].get(vertex_id)
            while True:
                children = adjacency.get(current)
                if not children:
                    break
                trie_children = trie_cursor[2] if trie_cursor else {}
                live_children = []
                for child in children:
                    avail = available(trie_children, child)
                    if avail <= 0:
                        continue
                    if weighted:
                        removed = trie_children.get(child)
                        mass = edges[(current, child)] * (
                            weights[child]
                            - (removed[1] if removed else 0.0))
                        live_children.append((child, avail, mass))
                    else:
                        live_children.append((child, avail, float(avail)))
                if weighted:
                    total_mass = sum(mass for _, _, mass in live_children)
                    pick = rng.random() * max(total_mass, 0.0)
                    current = live_children[-1][0]
                    for child, _, mass in live_children:
                        pick -= mass
                        if pick <= 0:
                            current = child
                            break
                else:
                    pick = rng.randrange(
                        sum(avail for _, avail, _ in live_children))
                    current = live_children[-1][0]
                    for child, avail, _ in live_children:
                        pick -= avail
                        if pick < 0:
                            current = child
                            break
                path.append(current)
                trie_cursor = (trie_cursor[2].get(current)
                               if trie_cursor else None)

            # Record the drawn path in the trie: below position i the
            # removed suffix weight is the product of the remaining edge
            # frequencies (1 at the terminal).
            suffix_weights = [1.0] * len(path)
            for i in range(len(path) - 2, -1, -1):
                suffix_weights[i] = (edges[(path[i], path[i + 1])]
                                     * suffix_weights[i + 1])
            cursor = trie_root
            for vertex, suffix_weight in zip(path, suffix_weights):
                child = cursor[2].get(vertex)
                if child is None:
                    child = [0, 0.0, {}]
                    cursor[2][vertex] = child
                child[0] += 1
                child[1] += suffix_weight
                cursor = child
            yield tuple(segments[i] for i in path)

    def display(self):
        for key, nextkeys in sorted(self.items(), key=lambda x: x):
            print('***', key.position, key.value)
            for nextkey, frequency in nextkeys.items():
                print(nextkey.value, frequency)
