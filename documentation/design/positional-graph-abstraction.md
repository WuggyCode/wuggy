# The positional-graph abstraction

*Design note, written during the 2.0 reengineering (branch
`claude/wuggy-2.0-reengineering`).*

## Context

The 2.0 rewrite replaced Wuggy's dict-of-dicts bigram store with an
interned integer DAG held in flat arrays
([`wuggy/utilities/segmentgraph.py`](../../wuggy/utilities/segmentgraph.py),
class `SegmentGraph`). Filters became boolean masks over the edge array,
`prune()` became a single backward-reachability sweep, and generation
gained exact path counting (`count_paths`) plus uniform and weighted
sampling-without-replacement modes, all driven by one backward dynamic
programming sweep over the layers.

A consequence worth recording: almost none of that machinery is about
language. It is a general data structure that happens to be carrying
subsyllabic segments today.

## What the structure actually is

Strip away the segments and lexicons and it is:

> **A weighted, layered DAG — equivalently an acyclic weighted
> finite-state automaton — over positional symbols, supporting
> composable hard-constraint masks, exact path counting, and unbiased
> sampling without replacement, all driven by one backward DP.**

Each *position* is a layer; each vertex is a `(position, symbol)` pair;
edges connect consecutive layers with weights equal to co-occurrence
counts (or summed token frequency). Every attested and every generable
sequence is a path from a start vertex to a vertex in the final layer.

## The four reusable primitives

1. **Compact representation of a combinatorial set as paths.** A set of
   sequences too large to materialize is held as a small graph.

2. **Constrain without materializing.** Each filter is a boolean AND
   over the edge array; the admissible set is narrowed by intersecting
   masks, never by enumerating and rejecting. This is what beats
   rejection sampling when the admissible set is a tiny fraction of the
   whole.

3. **Count exactly.** `count_paths` answers a #P-style question that is
   tractable *because the graph is a DAG* — one DP sweep. The weighted
   version of the same sweep is the **partition function** of the
   positional distribution.

4. **Sample uniformly or by weight, without replacement, exactly.**

## Applications, sorted by how cleanly they map

### Maps directly (same machinery, different alphabet)

- **Template-matched generation in general.** Wuggy is one instance of
  "generate items resembling a template, varying a controlled proportion
  of elements, drawn from attested statistics." The same engine drives
  procedural names, style-matched synthetic/fuzz test corpora, or
  de-novo biological sequence candidates (peptides, oligos, SMILES
  fragments) under positional-composition constraints and attested
  transition frequencies.

- **Wordlikeness / typicality scoring, not just generation.** Transition
  frequencies are already computed as a statistic; exposed as a
  normalized scorer (transition-product ÷ partition function) it is a
  general "how typical is this string for this lexicon" function —
  psycholinguistic norming, narrow-domain spell/OCR/ASR candidate
  rescoring, structural anomaly detection (low weight = atypical).

- **Design-space analytics for experiments.** "How many stimuli survive
  these controls?" answered instantly, plus quantities the partition
  function unlocks: **entropy of the constrained sub-language** and **KL
  divergence between two constrained sub-languages** — e.g. how much a
  frequency band or a segment restriction actually shrinks and reshapes
  the space.

### Maps with a modest extension

- **Layered constraint satisfaction / solution counting.** Read each
  position as a CSP variable and the masks as a constraint store:
  crossword filling, positionally-constrained scheduling, configurable-
  product (feature-model) enumeration. Uniform sampling of *solutions*
  and exact solution-counting are cheap here for the same DAG reason.

## Honest scope boundaries

- The model is **first-order and acyclic.** Higher-order context means
  vertices become `(position, k-gram)` — same machinery, more vertices.
  True cycles (a non-positional automaton) break the layered backward
  sweep and would need a general topological-order DP, or matrix methods
  in the cyclic case.

- The weighting is a **product of raw frequencies, not a smoothed
  probability model.** Fine for ranking and relative comparison, but
  unseen transitions are hard zeros; treat it as a partition function
  over attested mass, not a calibrated language model.

- The masks express **hard** constraints well; soft/weighted constraints
  beyond the frequency weighting are not modeled.

## Implication: the extraction seam

The core already contains no linguistics. This argues for a clean seam
between:

- a **domain-agnostic kernel** — call it a `PositionalGraph` /
  weighted-DAG module — owning interning, edge arrays, masks, counting,
  and the three sampling modes; and

- the **Wuggy-specific layer** — segments, ONC syllabification,
  lexicality, OLD20, plugin-driven parsing — sitting on top of it.

That is also exactly the boundary worth compiling if the counting-and-
sampling kernel ever becomes a Rust / `extendr` core: the kernel is the
part worth reusing and the part worth making fast, and it is separable
from everything that makes Wuggy specifically about pseudowords.

See [`extract-graph-kernel.prompt.md`](extract-graph-kernel.prompt.md)
for a task prompt that sketches this extraction.
