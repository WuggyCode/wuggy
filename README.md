# Wuggy: A multilingual pseudoword generator

<p align="center">
<img src=https://raw.githubusercontent.com/WuggyCode/wuggy/master/assets/wuggy_simplified.svg alt="Wuggy Logo">
</p>

Wuggy is a pseudoword generator particularly geared towards making nonwords for psycholinguistic experiments. Wuggy makes pseudowords in, but not limited to, Basque, Dutch, English, Estonian, French, German, Italian, Lithuanian, Serbian (Cyrillic and Latin), Spanish, and Vietnamese.

# GUI

A desktop application for Wuggy is available at [WuggyCode/wuggy-gui](https://github.com/WuggyCode/wuggy-gui). Pre-built macOS and Windows apps can be downloaded from its [releases page](https://github.com/WuggyCode/wuggy-gui/releases).

# Installation & Guide

Please refer to the [Wuggy Site](https://wuggycode.github.io/wuggy/) for installation and usage instructions.

# Development Environment

1. To clone the repository, use `git clone --recurse-submodules https://github.com/WuggyCode/wuggy`.
   If you do not clone the submodules, you will not download the language plugin files from the beginning.
   If you'd like to add the submodules after cloning without `--recurse-submodules`, use `git submodule update --init --recursive`.

2. Run `pip install -r dev-requirements.txt`. Note that some dependencies may require C extensions: pay close attention to any error messages you may receive during installation.
   Make sure you run this command using Python >= 3.8, optionally within a virtual environment.

### Generate documentation

Documentation is generated using `pdoc`. To update documentation locally , run `pdoc --html --output-dir build_documentation ./wuggy --force --template-dir ./documentation/templates`. Documentation is updated automatically to the live documentation site when changes are pushed to master using GitHub Actions.

### Installing the library

Wuggy is not currently published on PyPI. Install directly from GitHub:

```
pip install git+https://github.com/WuggyCode/wuggy.git
```

Note: `__init__.py` is explicitly required in every folder where you want to include the folder's `.py` files in the package.
This way the language plugins are not included in the package even if you have them downloaded on your development environment.
