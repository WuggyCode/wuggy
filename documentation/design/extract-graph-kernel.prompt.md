# Task prompt: sketch the extraction of a domain-agnostic graph kernel

Paste everything below the line into a new agent session, working from
the repository root on branch `claude/wuggy-2.0-reengineering`.

---

You are working in the Wuggy repository (a multilingual pseudoword
generator) on the local, unpushed branch `claude/wuggy-2.0-reengineering`.
The 2.0 rewrite turned the core bigram store into an interned integer DAG
with NumPy edge arrays, boolean-mask filters, exact path counting, and
uniform/weighted sampling. That core is in
`wuggy/utilities/segmentgraph.py` (class `SegmentGraph`, vertex namedtuple
`Vertex`). Background on why this is worth doing is in
`documentation/design/positional-graph-abstraction.md` — read it first.

## Goal

Sketch — and, if it comes out clean, implement — the extraction of a
**domain-agnostic weighted positional-DAG kernel** out from under the
Wuggy-specific `SegmentGraph`, with **no change in observable behavior**.
The deliverable is primarily a design: the module boundary, the kernel's
public interface, and exactly which state and methods move versus stay.
Implementing the refactor is welcome if it is verifiable against the
existing harness, but a crisp proposal with a skeleton is an acceptable
stopping point — do not force a half-finished rewrite.

## The intended seam

The kernel (proposed name `PositionalGraph`, in
`wuggy/utilities/positionalgraph.py`) should own everything that has no
knowledge of language:

- symbol interning and the `(position, symbol)` vertex identity, treating
  each symbol payload as an **opaque hashable** — the kernel must not
  reference `.letters`, `.hidden`, `Segment`, `SegmentH`, `separator`,
  `transform`, or any `language_plugin`;
- the flat edge arrays (`edge_src/dst/freq/pos`), the `edge_mask`, the
  position slices, and the view/mask machinery (`_view`,
  `_invalidate_caches`, `_edges`, `_adjacency`);
- generic filter *primitives*: an edge-mask filter and a vertex-predicate
  / vertex-pass-array filter, plus the numeric `frequency_filter` band
  logic (which is already language-free);
- `prune` / `_prune_in_place`, `set_start_vertices`, `get_frequencies`,
  `count_paths`, `_completion_counts`, and all of `generate` /
  `_generate_exhaustive` / `_generate_sampled` (the three search modes);
- cache serialization of the array state, with the linguistic payload
  reconstruction left to the subclass (see `to_cache_state` /
  `from_cache_state`, which currently reach into `language_plugin.Segment`
  — that reconstruction must move to the Wuggy layer).

`SegmentGraph` then becomes a thin layer (subclass or composition — you
decide, argue the trade-off) that adds only the linguistic parts:

- `load()` parsing a plugin data file via `language_plugin.separator` and
  `language_plugin.transform`;
- `attribute_filter` and `segmentset_filter`, re-expressed in terms of the
  kernel's generic vertex-predicate primitive (`segmentset_filter`'s use
  of `segment.letters` is the clearest linguistic dependency;
  `attribute_filter`'s `getattr(segment, attribute)` is nearly generic);
- `build_limit_frequencies` (uses named fields);
- the Segment/SegmentH reconstruction half of the cache round-trip.

Watch for: the mapping-compat methods (`__len__`, `__contains__`, `keys`,
`items`, `display`) are used by cold paths and tests — keep them working,
and decide which layer they belong to. `WuggyGenerator` refers to
`segment_graph`/`segment_graphs` and calls `attribute_filter`,
`frequency_filter`, `prune`, `set_start_vertices`, `generate(mode=...)`,
`get_frequencies`, `count_paths`; that public surface must not change.

## Hard constraints

- **No behavioral change.** This is a pure refactor.
- Keep the existing public API of `SegmentGraph` and `WuggyGenerator`
  intact (the rename to graph terminology already happened this branch;
  do not revert or re-alias it).
- Python only (numpy + rapidfuzz are the runtime deps). No new deps.

## How to verify

There is an equivalence harness and a sampling test suite. Set up a venv
with `numpy` and `rapidfuzz`, then:

1. `python tests/synthetic_plugin/make_data.py` (regenerates committed
   synthetic data deterministically; should be a no-op).
2. Capture behavior on the current commit **before** refactoring:
   `python tests/capture_behavior.py --out /tmp/before.json`.
3. Do the extraction.
4. `python tests/capture_behavior.py --out /tmp/after.json` and confirm
   `diff /tmp/before.json /tmp/after.json` is empty — this proves edge
   dumps (type and token weighting), start vertices, exhaustive
   generation sets, and all statistics are byte-identical.
5. `python tests/test_sampling.py` must pass (path counts, set-equality
   of all three generate modes, seeded determinism, weighted bias,
   generator API integration).

If you implement it, commit on the same branch with a message explaining
the seam; do not push. If you only sketch it, write the proposal to
`documentation/design/graph-kernel-extraction-plan.md` with the concrete
method/state partition and the proposed kernel interface.

## Deliverable

Either a verified refactor (both checks green) or a written extraction
plan precise enough to implement without rediscovering the seam — the
exact list of what moves, what stays, the kernel's public signature, and
how `SegmentGraph` re-expresses `attribute_filter` / `segmentset_filter`
on top of it.
