import random
from collections import defaultdict, namedtuple

import numpy as np

Vertex = namedtuple('Vertex', ['position', 'value'])

_SENTINEL = object()


class PositionalGraph:
    """
    A weighted, layered DAG over (position, symbol) vertices storing the next
    possible values, given a list of input sequences.

    Symbols are opaque hashable payloads; this class knows nothing about what
    they mean. Vertices are interned to integer ids; edges live in flat NumPy
    arrays (source, destination, frequency) sorted by source position.
    Filters return lightweight views that share the vertex/edge store and
    differ only in their boolean edge mask, so no filter ever copies the
    graph. On top of that store it supports composable hard-constraint masks
    (`vertex_pass_filter`, `frequency_filter`), pruning to complete paths,
    exact path counting, and exhaustive/uniform/weighted generation.
    """

    def __init__(self):
        self.start_vertices = {}
        # Shared vertex/edge store; populated by load_sequences() or shared
        # by views.
        self.vertex_symbols = []
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

    # ------------------------------------------------------------------
    # Construction

    def load_sequences(self, sequences):
        """
        Build the store from an iterable of (symbols, weight) pairs, where
        symbols is an indexable sequence of hashable payloads. Parallel
        edges accumulate their weights.
        """
        vertex_index = {}
        vertex_symbols = []
        vertex_positions = []
        edge_weights = {}

        def intern(position, symbol):
            key = (position, symbol)
            vertex_id = vertex_index.get(key)
            if vertex_id is None:
                vertex_id = len(vertex_symbols)
                vertex_index[key] = vertex_id
                vertex_symbols.append(symbol)
                vertex_positions.append(position)
            return vertex_id

        for symbols, weight in sequences:
            n = len(symbols)
            previous = intern(0, symbols[0])
            for j in range(1, n):
                current = intern(j, symbols[j])
                edge = (previous, current)
                edge_weights[edge] = edge_weights.get(edge, 0) + weight
                previous = current

        self.vertex_index = vertex_index
        self.vertex_symbols = vertex_symbols
        self.vertex_positions = np.array(vertex_positions, dtype=np.int32)
        nedges = len(edge_weights)
        src = np.empty(nedges, dtype=np.int32)
        dst = np.empty(nedges, dtype=np.int32)
        freq = np.empty(nedges, dtype=np.float64)
        for i, ((s, d), f) in enumerate(edge_weights.items()):
            src[i] = s
            dst[i] = d
            freq[i] = f
        # Sort edges by source position so pruning can sweep positions
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

    def _cache_arrays(self):
        """The array half of a picklable snapshot; symbols are the caller's."""
        return {
            'vertex_positions': self.vertex_positions,
            'edge_src': self.edge_src,
            'edge_dst': self.edge_dst,
            'edge_freq': self.edge_freq,
            'edge_pos': self.edge_pos,
        }

    def _restore_arrays(self, state, vertex_symbols):
        """Rebuild the store from _cache_arrays() output plus its symbols."""
        self.vertex_symbols = vertex_symbols
        self.vertex_positions = state['vertex_positions']
        self.vertex_index = {
            (int(position), symbol): vertex_id
            for vertex_id, (position, symbol)
            in enumerate(zip(self.vertex_positions, vertex_symbols))}
        self.edge_src = state['edge_src']
        self.edge_dst = state['edge_dst']
        self.edge_freq = state['edge_freq']
        self.edge_pos = state['edge_pos']
        self._build_position_slices()
        self.edge_mask = np.ones(len(self.edge_src), dtype=bool)
        self._invalidate_caches()
        self.set_start_vertices()

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
        view = type(self).__new__(type(self))
        view.start_vertices = {}
        view.vertex_symbols = self.vertex_symbols
        view.vertex_positions = self.vertex_positions
        view.vertex_index = self.vertex_index
        view.edge_src = self.edge_src
        view.edge_dst = self.edge_dst
        view.edge_freq = self.edge_freq
        view.edge_pos = self.edge_pos
        view._position_slices = self._position_slices
        view.edge_mask = edge_mask
        view._invalidate_caches()
        self._share_domain_state(view)
        return view

    def _share_domain_state(self, view):
        """Hook for subclasses to carry their own state onto filter views."""

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

    def _vertex_id(self, position, symbol):
        return self.vertex_index.get((position, symbol))

    # ------------------------------------------------------------------
    # Mapping-style compatibility (cold paths: display, dumps, limits)

    def __len__(self):
        return len(self._adjacency())

    def __contains__(self, key):
        vertex_id = self._vertex_id(key.position, key.value)
        return vertex_id is not None and vertex_id in self._adjacency()

    def keys(self):
        return [Vertex(int(self.vertex_positions[vertex_id]),
                     self.vertex_symbols[vertex_id])
                for vertex_id in self._adjacency()]

    def items(self):
        for vertex_id, children in self._adjacency().items():
            key = Vertex(int(self.vertex_positions[vertex_id]),
                       self.vertex_symbols[vertex_id])
            edges = self._edges()
            nextkeys = {
                Vertex(int(self.vertex_positions[child]),
                     self.vertex_symbols[child]):
                    edges[(vertex_id, child)]
                for child in children}
            yield key, nextkeys

    # ------------------------------------------------------------------
    # Public interface

    def set_start_vertices(self, reference_sequence=None, fields=None):
        adjacency = self._adjacency()
        self.start_vertices = {
            Vertex(0, self.vertex_symbols[vertex_id]): 0
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

    def edge_mask_filter(self, mask):
        """View keeping only active edges that also pass the given mask."""
        if len(self.edge_mask):
            mask = self.edge_mask & mask
        else:
            mask = self.edge_mask.copy()
        return self._view(mask)

    def vertex_pass_filter(self, vertex_pass, require_dst=True):
        """
        View keeping edges whose source vertex (and, unless require_dst is
        False, destination vertex) passes the given boolean array.
        """
        if len(self.edge_mask):
            mask = self.edge_mask & vertex_pass[self.edge_src]
            if require_dst:
                mask = mask & vertex_pass[self.edge_dst]
        else:
            mask = self.edge_mask.copy()
        return self._view(mask)

    def vertex_predicate_filter(self, predicate, require_dst=True):
        """vertex_pass_filter with the array built from predicate(position, symbol)."""
        vertex_pass = np.fromiter(
            (predicate(int(position), symbol)
             for position, symbol
             in zip(self.vertex_positions, self.vertex_symbols)),
            dtype=bool, count=len(self.vertex_symbols))
        return self.vertex_pass_filter(vertex_pass, require_dst=require_dst)

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
        """[(symbol value, vertex id or None if not in the graph), ...]"""
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
        single one-symbol sequence and therefore count as one path.
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
        Yield complete symbol sequences from the (filtered) graph.

        Modes:
            'exhaustive' — depth-first traversal with shuffled edge order
                (the classic behavior). Complete, but sequence order is
                biased toward low-branching regions of the graph.
            'uniform'    — every sequence exactly once, in unbiased random
                order (uniform sampling without replacement).
            'weighted'   — every sequence exactly once, sampled without
                replacement with probability proportional to the product
                of its transition frequencies, so the highest-weight
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
        symbols = self.vertex_symbols

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
                    yield tuple(symbols[i] for i in path) + (
                        symbols[vertex_id],)

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
        symbols = self.vertex_symbols
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
            yield tuple(symbols[i] for i in path)

    def display(self):
        for key, nextkeys in sorted(self.items(), key=lambda x: x):
            print('***', key.position, key.value)
            for nextkey, frequency in nextkeys.items():
                print(nextkey.value, frequency)
