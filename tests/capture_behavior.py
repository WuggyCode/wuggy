"""
Capture the observable behavior of the Wuggy core as order-independent data.

Run against two versions of the code and diff the JSON outputs to prove
behavioral equivalence:

    python tests/capture_behavior.py --out baseline.json   # on old code
    python tests/capture_behavior.py --out new.json        # on new code
    diff <(jq -S . baseline.json) <(jq -S . new.json)

Everything recorded is independent of dict ordering and random shuffling:
sorted edge dumps, exhaustive generation sets (hashed), and statistics for
a deterministic sample of candidates.
"""
import argparse
import codecs
import hashlib
import json
import sys
from fractions import Fraction
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(1, str(REPO / 'tests'))

from wuggy import WuggyGenerator  # noqa: E402
from wuggy.utilities.segmentgraph import SegmentGraph  # noqa: E402
from synthetic_plugin.synthetic import SyntheticLanguagePlugin  # noqa: E402

DATA_DIR = REPO / 'tests' / 'synthetic_plugin'
ENUMERATION_GUARD = 500_000
STAT_SAMPLE = 150


def jsonable(value):
    if isinstance(value, Fraction):
        return {'fraction': [value.numerator, value.denominator]}
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        # Normalize: the rewrite stores all frequencies as floats where the
        # old code mixed ints and floats.
        return round(float(value), 10)
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return value


def canonical(sequence):
    """Order-independent canonical string for a generated segment sequence."""
    return '|'.join(
        f'{segment.sequence_length}:{segment.segment_length}:{segment.letters}'
        for segment in sequence)


def edge_dump(graph):
    edges = []
    for key, nextkeys in graph.items():
        for nextkey, frequency in nextkeys.items():
            edges.append([key.position, list(key.value),
                          nextkey.position, list(nextkey.value),
                          float(frequency)])
    edges.sort()
    return edges


def start_vertex_dump(graph):
    return sorted([key.position, list(key.value)] for key in graph.start_vertices)


def enumerate_all(graph):
    """Fully drain graph.generate(); returns {canonical: sequence}."""
    sequences = {}
    for sequence in graph.generate():
        sequences[canonical(sequence)] = sequence
        if len(sequences) > ENUMERATION_GUARD:
            raise RuntimeError('enumeration exceeded guard; shrink test data')
    return sequences


def summarize(sequences):
    ordered = sorted(sequences)
    return {
        'count': len(ordered),
        'sha256': hashlib.sha256('\n'.join(ordered).encode()).hexdigest(),
        'sample': ordered[:400],
    }


def capture_statistics(generator, sequences):
    """Statistics for a deterministic sample of enumerated sequences."""
    plugin = generator.language_plugin
    stats = {}
    for canon in sorted(sequences)[:STAT_SAMPLE]:
        sequence = sequences[canon]
        stats[canon] = {
            name: jsonable(getattr(plugin, 'statistic_' + name)(generator, sequence))
            for name in generator.supported_statistics}
    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    args = parser.parse_args()

    generator = WuggyGenerator()
    generator.load('synthetic_test',
                   local_language_plugin=SyntheticLanguagePlugin())
    result = {'chain_edges_type': edge_dump(generator.segment_graph)}

    token_graph = SegmentGraph(generator.language_plugin)
    with codecs.open(DATA_DIR / 'data.txt', 'r', encoding='utf-8') as f:
        token_graph.load(f, token=True)
    result['chain_edges_token'] = edge_dump(token_graph)

    lookup = sorted(generator.lookup_lexicon.items())
    one_syllable = [w for w, seg in lookup if '-' not in seg][:5]
    two_syllable = [w for w, seg in lookup if '-' in seg][:4]
    result['reference_words'] = one_syllable + two_syllable

    result['references'] = {}
    for word in result['reference_words']:
        segments = generator.lookup_reference_segments(word)
        generator.set_reference_sequence(segments)
        reference = generator.reference_sequence
        maxpos = len(reference) - 1
        entry = {
            'segments': segments,
            'ref_frequencies': jsonable(generator.reference_sequence_frequencies),
            'ref_statistics': jsonable(generator.reference_statistics),
        }

        plain = generator.segment_graph.prune(maxpos)
        plain.set_start_vertices(reference)
        entry['startkeys_nofilter'] = start_vertex_dump(plain)
        entry['nofilter'] = summarize(enumerate_all(plain))

        attr_subgraph = generator.segment_graph.attribute_filter(
            reference, 'segment_length')
        attr_pruned = attr_subgraph.prune(maxpos)
        attr_pruned.set_start_vertices(reference)
        entry['attr_edges'] = edge_dump(attr_pruned)
        attr_sequences = enumerate_all(attr_pruned)
        entry['attr'] = summarize(attr_sequences)
        entry['attr_stats'] = capture_statistics(generator, attr_sequences)

        freq_subgraph = attr_subgraph.frequency_filter(reference, 4, 4)
        freq_pruned = freq_subgraph.prune(maxpos)
        freq_pruned.set_start_vertices(reference)
        entry['attr_freq4'] = summarize(enumerate_all(freq_pruned))

        result['references'][word] = entry

    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=1, sort_keys=True)
    counts = [result['references'][w]['nofilter']['count']
              for w in result['reference_words']]
    print(f'captured {len(counts)} references, '
          f'enumeration sizes: {counts}', file=sys.stderr)


if __name__ == '__main__':
    main()
