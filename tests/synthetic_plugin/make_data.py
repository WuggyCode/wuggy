"""
Deterministically generate a synthetic language for tests and benchmarks.

Words are built from CV(C) syllables segmented as onset:nucleus:coda, the
same shape official orthographic plugins use with copy_onc. Running this
script regenerates the committed data files bit-for-bit (fixed seed).
"""
import argparse
import random
from pathlib import Path

ONSETS = ['b', 'k', 'd', 'f', 'g', 'l', 'm', 'n', 'p', 'r',
          's', 't', 'v', 'w', 'z', 'st', 'tr', 'pl', 'kr', 'sn']
NUCLEI = ['a', 'e', 'i', 'o', 'u', 'aa', 'ee', 'oo', 'ie', 'ei']
CODAS = ['', 'k', 'l', 'm', 'n', 'p', 'r', 's', 't', 'st', 'rk', 'nd']


def make_words(n, seed=1234, max_syllables=2):
    rng = random.Random(seed)
    words = {}
    while len(words) < n:
        nsyllables = rng.randint(1, max_syllables)
        syllables = [(rng.choice(ONSETS), rng.choice(NUCLEI), rng.choice(CODAS))
                     for _ in range(nsyllables)]
        plain = ''.join(''.join(syllable) for syllable in syllables)
        if plain in words:
            continue
        segmented = '-'.join(':'.join(syllable) for syllable in syllables)
        frequency = max(1, int(rng.lognormvariate(2.0, 1.5)))
        words[plain] = (segmented, frequency)
    return words


def write_language(words, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    items = sorted(words.items())
    with open(outdir / 'data.txt', 'w', encoding='utf-8') as f:
        for plain, (segmented, frequency) in items:
            f.write(f'{plain}\t{segmented}\t{frequency}\n')
    with open(outdir / 'lookup.txt', 'w', encoding='utf-8') as f:
        for plain, (segmented, _) in items:
            f.write(f'{plain}\t{segmented}\n')
    with open(outdir / 'lexicon.txt', 'w', encoding='utf-8') as f:
        for plain, (_, frequency) in items:
            f.write(f'{plain}\t{frequency}\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--words', type=int, default=220)
    parser.add_argument('--seed', type=int, default=1234)
    parser.add_argument('--max-syllables', type=int, default=2)
    parser.add_argument('--out', default=str(Path(__file__).parent))
    args = parser.parse_args()
    write_language(
        make_words(args.words, args.seed, args.max_syllables), args.out)
    print(f'wrote {args.words} words to {args.out}')
