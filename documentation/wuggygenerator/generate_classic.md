# Generate Classic Examples

## In what format are pseudowords returned?

Pseudowords are returned in a dictionary format in a verbose format, containing details such as statistics. Below is an example return value for a pseudoword generated for `car`.

```python
{
    "word": "car",
    "segments": "car",
    "pseudoword": "cag",
    "statistics": {
        "lexicality": "N",
        "ned1": 24,
        "old20": 1.0,
        "overlap": 2,
        "overlap_ratio": Fraction(2, 3),
        "plain_length": 1,
        "transition_frequencies": {0: 304, 1: 92, 2: 22, 3: 80},
    },
    "difference_statistics": {
        "ned1": -4,
        "old20": 0.050000000000000044,
        "plain_length": 0,
        "transition_frequencies": {0: 0, 1: 0, 2: 8, 3: -11},
    },
}
```


## Generating pseudowords (default settings)

In this example, we will generate pseudowords for the English words `car` and `bicycle`. We will print these pseudowords to the console.

```python
from wuggy.generators.wuggygenerator import WuggyGenerator

g = WuggyGenerator()
g.load("orthographic_english")
for match in g.generate_classic(["car", "bicycle"]):
    print(match["pseudoword"])
```

The code above first loads the `orthographic_english` language plugin. After this, the `generate_classic` method is called with a list of reference sequences for which we want to generate pseudowords. The method returns a list of pseudoword matches. These matches consist of dictionairies with many details about the match, such as relevant statistics. Since we are only interested in the generated pseudowords, we print the value assigned to the key `pseudoword`. 

## Generating pseudowords (custom settings)

In this example, we will generate pseudowords for the English words `car` and `bicycle`, this time using some custom settings. The `generate_classic` method takes several optional arguments which can be used to change the output of the generator. The defaults are usually great for generating useful pseudowords, so this example will only change two parameters. 

```python
from wuggy.generators.wuggygenerator import WuggyGenerator

g = WuggyGenerator()
g.load("orthographic_english")
for match in g.generate_classic(
    ["car", "bicycle"],
    ncandidates_per_sequence=30, max_search_time_per_sequence=25):
    print(match["pseudoword"])
```

The code above will ensure that, per sequence in the input list, a maximum of 30 candidates will be generated. By default, Wuggy only has 10 seconds to find this amount of candidates per sequence. For this reason, we can set the `max_search_time_per_sequence` to a higher amount to ensure that 30 sequences can be generated in time.

## Generating pseudowords and exporting to CSV

Since Wuggy is a Python library, its output can be easily used by other modules to perform actions such as exporting pseudowords to CSV. This can be done manually, although Wuggy includes a built-in helper method to easily export classic pseudoword matches to a CSV file:

```python
from csv import DictWriter

from wuggy.generators.wuggygenerator import WuggyGenerator

g = WuggyGenerator()
g.load("orthographic_english")
pseudoword_matches = g.generate_classic(["car"])
g.export_classic_pseudoword_matches_to_csv(pseudoword_matches, "./pseudowords.csv")
```

By using this method, the nested dictionary will be flattened so that the resulting CSV can be easily interpreted by your software of choice.