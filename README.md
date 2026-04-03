# Wuggy: A multilingual pseudoword generator

<p align="center">
<img src=https://raw.githubusercontent.com/WuggyCode/wuggy/master/assets/wuggyIcon.jpg alt="Wuggy Logo">
</p>

Wuggy is a pseudoword generator particularly geared towards making nonwords for psycholinguistic experiments. Wuggy makes pseudowords in, but not limited to, Basque, Dutch, English, French, German, Serbian (Cyrillic and Latin), Spanish, and Vietnamese.

# Download

Pre-built desktop apps are available on the [GitHub Releases page](https://github.com/WuggyCode/wuggy/releases):

- **macOS** — download `Wuggy-<version>.dmg`, open it, and drag Wuggy to your Applications folder.
- **Windows** — download `Wuggy-<version>-windows.zip`, extract it, and run `Wuggy.exe`.

# Installation & Guide

Please refer to the [Wuggy Site](https://wuggycode.github.io/wuggy/) for installation and usage instructions.

# GUI

Wuggy includes a browser-based graphical interface built on Flask and pywebview. It supports all languages, lets you syllabify and generate pseudowords interactively, and exports results to CSV.

### Running the GUI

1. Install the GUI dependencies:
   ```
   pip install -r requirements-gui.txt
   ```

2. Launch the GUI from the repository root:
   ```
   python run_gui.py
   ```
   This opens a native desktop window (powered by pywebview).

### Launch options

| Flag | Description |
|------|-------------|
| *(none)* | Opens a native desktop window |
| `--browser` | Starts the Flask server and opens your default browser |
| `--server` | Starts Flask only — no window or browser (useful for remote/headless use) |
| `--port PORT` | Use a specific port (default: auto) |
| `--host HOST` | Bind to a specific host (default: `127.0.0.1`) |

### macOS app bundle

A standalone `.app` and `.dmg` can be built with PyInstaller:

```
pip install pyinstaller
pyinstaller wuggy.spec --noconfirm
```

Or use the convenience script (requires [create-dmg](https://github.com/create-dmg/create-dmg)):

```
./build_dmg.sh
```

The output is `dist/Wuggy-1.2.0.dmg`.

# Development Environment

1. To clone the repository, use `git clone --recurse-submodules https://github.com/WuggyCode/wuggy`.
   If you do not clone the submodules, you will not download the language plugin files from the beginning.
   If you'd like to add the submodules after cloning without `--recurse-submodules`, use `git submodule update --init --recursive`.

2. Run `pip install -r dev-requirements.txt`. Note that some dependencies may require C extensions: pay close attention to any error messages you may receive during installation.
   Make sure you run this command using Python >= 3.8, optionally within a virtual environment.

### Generate documentation

Documentation is generated using `pdoc`. To update documentation locally , run `pdoc --html --output-dir build_documentation ./wuggy --force --template-dir ./documentation/templates`. Documentation is updated automatically to the live documentation site when changes are pushed to master using GitHub Actions.

### Uploading a new version to PyPi

Prerequisite: ensure that `setup.py` contains the right information, including the desired version number!

1. `python setup.py sdist bdist_wheel`
2. `twine upload dist/*` (ensure dist folder does not contain old versions!) (you must enter your PyPi credentials here)
   (for staging/testing, use `twine upload --repository testpypi dist/*` and `pip install --extra-index-url https://testpypi.python.org/pypi Wuggy`)

Note: `__init__.py` is explicitly required in every folder where you want to include the folder's `.py` files in the package.
This way the language plugins are not included in the package even if you have them downloaded on your development environment.
