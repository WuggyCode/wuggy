BaseLanguagePlugin is the Base class used for all official Wuggy language plugins and custom local language plugins.

# Examples

## Creating a custom language plugin

### Based on an official language plugin
In this example, we will start off creating a custom language plugin. Create an empty Python file called `your_project_file.py` and try to run the following code within this file:

```python
from wuggy import WuggyGenerator

g = WuggyGenerator()
g.load("orthographic_english")
for w in g.generate_classic(["wuggy"]):
    print(w)
```

Uh oh! You should be getting an error that `wuggy` is not a word in the `orthographic_english` lexicon. Let's assume `wuggy` is an important slang word which is essential for our research. We need to customize the `orthographic_english` lexicon and add the word `wuggy`. 

1. To keep things simple, let's redownload the `orthographic_english` plugin to our local machine in the folder your project is currently in. First, create a new folder in the same directory as the Python file you just tested the script in. Call it `modified_orthographic_english`. Visit the [official Wuggy language data repository](https://github.com/WuggyCode/wuggy_language_plugin_data) and download the plugin from here and save both the `.py` and `.txt` files in the root of the `modified_orthographic_english` folder. Your project folder structure should now look like this:

```
your_project_file.py
📁modified_orthographic_english
    -- orthographic_english.py
    -- orthographic_english.txt
```

1. The `orthographic_english.py` file needs to be modified slightly to accomodate for the different folder structure, since the plugin is used outside of the official plugin folder. Go into this file and replace the line `from ...baselanguageplugin import BaseLanguagePlugin` with `from wuggy import BaseLanguagePlugin`.

2. Now we are getting somewhere: you already have a functional local language plugin which you can import. Let's ensure that you have followed the steps properly. Replace the contents of `your_project_file.py` with:
```python
from wuggy import WuggyGenerator

from my_custom_plugin.orthographic_english import LanguagePlugin

g = WuggyGenerator()
g.load("modified_orthographic_english", LanguagePlugin())
for w in g.generate_classic(["wuggy"]):
    print(w)
```

This code passes a custom language plugin name to wuggy, together with an instance of the imported LanguagePlugin class defined in `orthographic_english.py`. Note how when you run this code, the language plugin loads, but of course you still receive an error since `wuggy` is not a valid word in the lexicon.

4. To modify the language lexicon, browse into `orthographic_english.txt`. Each word is written in the format `WORD{tab}WORD_IN_SYLLABLES{tab}OCCURRENCE_PER_MILLION_WORDS` (the three word elements are split using a single tab: you must adhere to this for each line in the lexicon). To add `wuggy` to the lexicon, paste `wuggy	wug-gy	0.01` at the end of the document (we assume that wuggy occurs 0.01 times per million words).

Now, when you execute `orthographic_english.py` again, you should be generating pseudowords for the word `wuggy`!