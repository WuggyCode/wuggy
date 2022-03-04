# Wuggy: A multilingual pseudoword generator

<p align="center">
<img src=https://raw.githubusercontent.com/WuggyCode/wuggy/master/assets/wuggyIcon.jpg alt="Wuggy Logo">
</p>

Wuggy is a pseudoword generator particularly geared towards making nonwords for psycholinguistic experiments. Wuggy makes pseudowords in, but not limited to, Basque, Dutch, English, French, German, Serbian (Cyrillic and Latin), Spanish, and Vietnamese.

# Installation & Guide

Please refer to the [Wuggy Site](https://wuggycode.github.io/wuggy/) for installation and usage instructions.

# Development Environment

1. To clone the repository, use `git clone --recurse-submodules https://github.com/WuggyCode/wuggy`.
   If you do not clone the submodules, you will not download the language plugin files from the beginning.
   If you'd like to add the submodules after cloning without `--recurse-submodules`, use `git submodule update --init --recursive`.

2. Run `pip install -r dev-requirements.txt`. Note that some dependencies may require C extensions: pay close attention to any error messages you may receive during installation.
   Make sure you run this command using Python >= 3.6, optionally within a virtual environment.

### Generate documentation

Documentation is generated using `pdoc`. To update documentation locally , run `pdoc --html --output-dir build_documentation ./wuggy --force --template-dir ./documentation/templates`. Documentation is updated automatically to the live documentation site when changes are pushed to master using GitHub Actions.

### Uploading a new version to PyPi

Prerequisite: ensure that `setup.py` contains the right information, including the desired version number!

1. `python setup.py sdist bdist_wheel`
2. `twine upload dist/*` (ensure dist folder does not contain old versions!) (you must enter your PyPi credentials here)
   (for staging/testing, use `twine upload --repository testpypi dist/*` and `pip install --extra-index-url https://testpypi.python.org/pypi Wuggy`)

Note: `__init__.py` is explicitly required in every folder where you want to include the folder's `.py` files in the package.
This way the language plugins are not included in the package even if you have them downloaded on your development environment.
