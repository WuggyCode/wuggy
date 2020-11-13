# What is Wuggy?

Wuggy is a pseudoword generator particularly geared towards making nonwords for psycholinguistic experiments. Wuggy makes pseudowords in, but not limited to, Basque, Dutch, English, French, German, Serbian (Cyrillic and Latin), Spanish, and Vietnamese.

[Download our paper on Wuggy here](http://crr.ugent.be/papers/Wuggy_BRM.pdf) and cite as Keuleers, E., & Brysbaert, M. (2010). Wuggy: A multilingual pseudoword generator. *Behavior Research Methods* 42(3), 627-633

Wuggy is a pseudoword generator that uses an innovative approach for generating pseudowords, combining the best of existing approaches.

* Traditionally, lists of pseudowords have been available that are based on combining subsyllabic elements that are legal in the language of choice. For instance, by combining the legal onset b (as in bat) with a legal nucleus u (as in fun) and a legal coda p (as in ship), we get the pseudoword bup, which is legal (pronounceable) in English. The problem with this approach is that it leads to a combinatorial explosion. For monosyllabic words, the list is still tractable (hundreds of thousands of pseudowords), but combining elements into polysyllabic strings quickly leads to billions of possibilities. Choosing an appropriate pseudoword for your needs becomes an impossibility because there are too many options to match.

* Other approaches are based on guessing good pseudowords by combining high frequency letter sequences. These approaches make it possible to produce longer sequences, but these sequences are not necessarily legal in the language, and, by design, the generated sequences do not contain low frequency letters.
The core algorithm in Wuggy is able to generate all possible pseudowords in the language (depending on the quality of its input, it may make a few impossible ones). However, by employing some smart tricks, Wuggy doesn’t have to generate all these pseudowords before it knows which pseudoword is good for you. In fact, the tougher the restrictions you give Wuggy, the faster it will find the solution. Wuggy does this by restricting the model of the language before it starts generating candidates instead of searching through the list afterwards.

The core algorithm in Wuggy is able to generate all possible pseudowords in the language (depending on the quality of its input, it may make a few impossible ones). However, by employing some smart tricks, Wuggy doesn’t have to generate all these pseudowords before it knows which pseudoword is good for you. In fact, the tougher the restrictions you give Wuggy, the faster it will find the solution. Wuggy does this by restricting the model of the language before it starts generating candidates instead of searching through the list afterwards.

# Overview of operation

This new version of Wuggy is a Python library intended to allow for easier access to pseudowords within research projects.

## How do I get started?

### Installing Wuggy

Simply run `pip install Wuggy` and get going! It's never been easier.

### Using Wuggy

Starting out, it is recommended to use the [classic](generators/wuggygenerator.html#wuggy.generators.wuggygenerator.WuggyGenerator.generate_classic) mode of Wuggy to quickly get desired pseudowords.
As you get familiar with Wuggy and realize its broad potential, you may want to consider customizing Wuggy's behaviour using the [advanced](generators/wuggygenerator.html#wuggy.generators.wuggygenerator.WuggyGenerator.generate_advanced) mode of Wuggy. In addition, you can create [custom language plugins](plugins/baselanguageplugin.html) aligning with the needs of your specific research. You can customize official language plugins such as `orthographic_english` and add slang words, or even go as far to generate pseudowords for Klingon.

# FAQ

**How does this version of Wuggy differ and improve upon the legacy version?**

This version of Wuggy is a Python library for a modern audience accustomed to using Python. It allows you to use the well known Wuggy algorithm within existing or new coding projects without the overhead of manually copying pseudowords, as has been the case in the past. For the more daring and experience Wuggy users, Wuggy is more open than before, allowing you to create [your own language plugin](plugins/baselanguageplugin.html).

If using Wuggy in a Python environment sounds scary, there is no need to fear. This version of Wuggy comes with a [`classic` generation method](generators/wuggygenerator.html#generate-classic-examples), with defaults set exactly as they were in the legacy Wuggy version.

**Frequently Asked Questions**

I just want a few pseudowords for my stimuli. Do I really need to install Wuggy? Can’t you just give me some?

Downloading and installing Wuggy is painless and, with some Python experience, you'll have pseudowords within a few minutes.

Ok, but what kind of pseudowords can I expect from Wuggy?

The list below shows Wuggy’s output using default settings for some English words with an increasing number of syllables. For each word, we show 5 generated pseudowords.

| Word            | Pseudoword      |
| --------------- | --------------- |
| car             | cas             |
| car             | cag             |
| car             | har             |
| car             | rar             |
| car             | dar             |
| park            | paze            |
| park            | paft            |
| park            | palt            |
| park            | parn            |
| park            | paff            |
| border          | bowper          |
| border          | bowmer          |
| border          | curder          |
| border          | besder          |
| border          | berber          |
| patrol          | pagril          |
| patrol          | pabril          |
| patrol          | pachil          |
| patrol          | pablyl          |
| patrol          | paplil          |
| assistant       | assissite       |
| assistant       | astontant       |
| assistant       | astortant       |
| assistant       | attostant       |
| assistant       | attustant       |
| professor       | proforror       |
| professor       | proforlor       |
| professor       | profindor       |
| professor       | profarror       |
| professor       | profarlor       |
| helicopter      | tosicolter      |
| helicopter      | tosicotter      |
| helicopter      | bolicyrter      |
| helicopter      | bolicytter      |
| helicopter      | bolicylter      |
| transportation  | trathmollation  |
| transportation  | trathnollation  |
| transportation  | trathtollation  |
| transportation  | tranctollation  |
| transportation  | traugmollation  |
| matrimonial     | sorbiconial     |
| matrimonial     | sorbilonial     |
| matrimonial     | sorbimotial     |
| matrimonial     | sorsiconial     |
| matrimonial     | sorsilonial     |
| congratulations | concrubonations |
| congratulations | concruborations |
| congratulations | concrulonations |
| congratulations | concrulorations |
| congratulations | concruponations |