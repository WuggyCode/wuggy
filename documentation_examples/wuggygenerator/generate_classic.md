# Examples

## Printing out pseudowords

In this example, we will generate pseudowords for the English words `car` and `bicycle`. We will print these pseudowords to the console.

```python
from wuggy.generators.wuggygenerator import WuggyGenerator

g = WuggyGenerator()
g.load("orthographic_english")
for match in g.generate_classic(["car", "bicycle"]):
    print(match["pseudoword"])
```

The code above first loads the `orthographic_english` language plugin. After this, the `generate_classic` method is called with a list of reference sequences for which we want to generate pseudowords. The method returns a list of pseudoword matches. These matches consist of dictionairies with many details about the match, such as relevant statistics. Since we are only interested in the generated pseudowords, we print the value assigned to the key `pseudoword`. 