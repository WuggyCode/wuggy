# Generate Advanced Examples

## In what format are pseudowords returned?

Using the advanced generate method, Wuggy will return a generator which you can iterate over to generate pseudowords, e.g:

```python
from wuggy.generators.wuggygenerator import WuggyGenerator

g = WuggyGenerator()
g.load("orthographic_english")
g.set_reference_sequence("balloon")
for sequence in g.generate_advanced(clear_cache=False):
    print(sequence)
```
(note that this example returns rather useless pseudowords since there are no restrictions set)

## Generating Pseudowords (with sensible settings)

Generating pseudowords using this method requires good knowledge of Wuggy in order to generate pseudowords which, for example, closely resemble the origin reference word.

The following example uses advanced generation to set a number of restrictions on generated pseudowords.

1. Each origin word will generate a maximum of 10 pseudowords
2. Each pseudoword must be a non-word
3. Each pseudoword must overlap 2/3 subsyllabic segments
4. The frequency filter is increased if not enough matches are found within a given band (this is concentric search)
5. Sensible attribute filters are enforced

```python
from fractions import Fraction

from wuggy.generators.wuggygenerator import WuggyGenerator

words = ["trumpet", "car"]
g = WuggyGenerator()
g.load("orthographic_english")
ncandidates = 10
for word in words:
    g.set_reference_sequence(g.lookup_reference_segments(word))
    g.set_attribute_filter('sequence_length')
    g.set_attribute_filter('segment_length')
    g.set_statistic('overlap_ratio')
    g.set_statistic('plain_length')
    g.set_statistic('transition_frequencies')
    g.set_statistic('lexicality')
    g.set_statistic('ned1')
    g.set_output_mode('syllabic')
    j = 0
    for i in range(1, 10, 1):
        g.set_frequency_filter(2**i, 2**i)
        for sequence in g.generate_advanced(clear_cache=False):
            match = False
            if (g.statistics['overlap_ratio'] == Fraction(2, 3) and
                    g.statistics['lexicality'] == "N"):
                match = True
            if match == True:
                print(sequence)
                j = j+1
                if j > ncandidates:
                    break
        if j > ncandidates:
            break
```

Note how using `generate_advanced` requires setting many parameters and candidate check logic yourself. 
Make sure that `generate_classic` does not suit your needs before using this method, as its low level nature makes it easy to return pseudowords which do not fit your needs.