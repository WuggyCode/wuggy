# Generate Classic Examples

## In what format are pseudowords returned?

Pseudowords are returned in a dictionairy format in a verbose format, containing details such as statistics. Below is an example return value for a pseudoword generated for `car`.

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

In this example, we will generate pseudowords for the English words `car`, this time using some custom settings.

```python
from wuggy.generators.wuggygenerator import WuggyGenerator

g = WuggyGenerator()
g.load("orthographic_english")
for match in g.generate_classic(["car", "bicycle"]):
    print(match["pseudoword"])
```

The code above first loads the `orthographic_english` language plugin. After this, the `generate_classic` method is called with a list of reference sequences for which we want to generate pseudowords. The method returns a list of pseudoword matches. These matches consist of dictionairies with many details about the match, such as relevant statistics. Since we are only interested in the generated pseudowords, we print the value assigned to the key `pseudoword`. 