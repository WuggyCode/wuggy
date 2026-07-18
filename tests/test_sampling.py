"""
Tests for count_paths() and the uniform/weighted generation modes.

Both sampling modes draw without replacement, so they must yield exactly
the same set of sequences as exhaustive traversal, each exactly once.
Runnable directly: python tests/test_sampling.py
"""
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(1, str(REPO / 'tests'))

from wuggy import WuggyGenerator  # noqa: E402
from synthetic_plugin.synthetic import SyntheticLanguagePlugin  # noqa: E402

PERMUTATION_SIZE_CAP = 30_000


def make_generator():
    generator = WuggyGenerator()
    generator.load('synthetic_test',
                   local_language_plugin=SyntheticLanguagePlugin())
    return generator


def canonical(sequence):
    return '|'.join(
        f'{s.sequence_length}:{s.segment_length}:{s.letters}'
        for s in sequence)


def prepared_subgraphs(generator):
    """(label, subgraph, reference) for a few filter configurations."""
    lookup = sorted(generator.lookup_lexicon.items())
    references = ([w for w, seg in lookup if '-' not in seg][:3]
                  + [w for w, seg in lookup if '-' in seg][:2])
    for word in references:
        generator.set_reference_sequence(
            generator.lookup_reference_segments(word))
        reference = generator.reference_sequence
        maxpos = len(reference) - 1
        attr = generator.segment_graph.attribute_filter(
            reference, 'segment_length')
        pruned = attr.prune(maxpos)
        pruned.set_start_vertices(reference)
        yield f'{word}/attr', pruned, reference
        banded = attr.frequency_filter(reference, 4, 4)
        banded = banded.prune(maxpos)
        banded.set_start_vertices(reference)
        yield f'{word}/attr+freq4', banded, reference


def test_permutation_equivalence_and_counts():
    generator = make_generator()
    tested = 0
    for label, subgraph, _ in prepared_subgraphs(generator):
        expected = subgraph.count_paths()
        if expected == 0 or expected > PERMUTATION_SIZE_CAP:
            continue
        exhaustive = [canonical(s) for s in subgraph.generate()]
        assert len(exhaustive) == expected, (
            f'{label}: count_paths {expected} != exhaustive {len(exhaustive)}')
        for mode in ('uniform', 'weighted'):
            drawn = [canonical(s) for s in
                     subgraph.generate(mode=mode, rng=random.Random(7))]
            assert len(drawn) == expected, (
                f'{label}/{mode}: yielded {len(drawn)}, expected {expected}')
            assert set(drawn) == set(exhaustive), (
                f'{label}/{mode}: sequence sets differ from exhaustive')
        tested += 1
    assert tested >= 4, f'only {tested} subgraphs were small enough to test'
    print(f'permutation equivalence ok over {tested} subgraphs')


def test_seeded_determinism():
    generator = make_generator()
    for label, subgraph, _ in prepared_subgraphs(generator):
        if not 0 < subgraph.count_paths() <= PERMUTATION_SIZE_CAP:
            continue
        for mode in ('uniform', 'weighted'):
            first = [canonical(s) for s in
                     subgraph.generate(mode=mode, rng=random.Random(123))]
            second = [canonical(s) for s in
                      subgraph.generate(mode=mode, rng=random.Random(123))]
            assert first == second, f'{label}/{mode}: seeded runs differ'
        break
    print('seeded determinism ok')


def path_weight(subgraph, sequence, reference):
    frequencies = subgraph.get_frequencies(sequence)
    weight = 1.0
    for value in frequencies.values():
        weight *= max(value, 1e-12)
    return weight


def test_weighted_mode_prefers_frequent_paths():
    generator = make_generator()
    for label, subgraph, reference in prepared_subgraphs(generator):
        if not 1_000 < subgraph.count_paths() <= PERMUTATION_SIZE_CAP:
            continue
        head = 25
        uniform_weights, weighted_weights = [], []
        for seed in range(20):
            drawn = subgraph.generate(mode='uniform',
                                      rng=random.Random(seed))
            uniform_weights.extend(
                path_weight(subgraph, s, reference)
                for _, s in zip(range(head), drawn))
            drawn = subgraph.generate(mode='weighted',
                                      rng=random.Random(seed))
            weighted_weights.extend(
                path_weight(subgraph, s, reference)
                for _, s in zip(range(head), drawn))
        mean_uniform = sum(uniform_weights) / len(uniform_weights)
        mean_weighted = sum(weighted_weights) / len(weighted_weights)
        assert mean_weighted > mean_uniform, (
            f'{label}: weighted mode did not prefer frequent paths '
            f'({mean_weighted:.1f} <= {mean_uniform:.1f})')
        print(f'weighted-bias ok on {label}: mean path weight '
              f'{mean_weighted:.1f} (weighted) vs {mean_uniform:.1f} (uniform)')
        return
    raise AssertionError('no subgraph of suitable size found')


def test_generator_api_integration():
    generator = make_generator()
    words = sorted(generator.lookup_lexicon)[:3]
    for search_mode in ('uniform', 'weighted'):
        random.seed(11)
        matches = generator.generate_classic(
            words, ncandidates_per_sequence=5, max_search_time_per_sequence=3,
            search_mode=search_mode)
        assert matches, f'no classic matches in {search_mode} mode'
        assert all(m['statistics']['lexicality'] == 'N' for m in matches)
    # generate_classic leaves its last concentric frequency filter set;
    # clear it so the advanced generator starts from the full graph.
    generator.clear_frequency_filter()
    generator.clear_attribute_filters()
    generator.set_reference_sequence(
        generator.lookup_reference_segments(words[0]))
    generator.set_attribute_filter('segment_length')
    generator.set_output_mode('plain')
    random.seed(11)
    advanced = list(generator.generate_advanced(mode='uniform'))
    assert advanced and len(advanced) == len(set(advanced))
    try:
        generator.segment_graph.generate(mode='nonsense')
    except ValueError:
        pass
    else:
        raise AssertionError('unknown mode did not raise ValueError')
    print(f'generator API integration ok '
          f'({len(advanced)} advanced uniform outputs)')


if __name__ == '__main__':
    test_permutation_equivalence_and_counts()
    test_seeded_determinism()
    test_weighted_mode_prefers_frequent_paths()
    test_generator_api_integration()
    print('all sampling tests passed')
