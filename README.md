# Wuggy: A multilingual pseudoword generator

<p align="center">
<img src=http://crr.ugent.be/wordpress/wp-content/uploads/2010/04/wug.jpg alt="Wuggy Logo">
</p>

This repository is a work-in-progress and will be finalized in a couple of months.

# Installation

## Development Environment

1. To clone the repository, use `git clone --recurse-submodules https://github.com/Zenulous/wuggy`.
   If you do not clone the submodules, you will not download the language plugin files from the beginning.
   If you'd like to add the submodules after cloning without `--recurse-submodules`, use `git submodule update --init --recursive`.

2. Run `pip install -r dev-requirements.txt`. Note that some dependencies may require C extensions: pay close attention to any error messages you may receive during installation.
   Make sure you run this command using Python >= 3.6, optionally within a virtual environment.
