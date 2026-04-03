# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the Wuggy macOS app bundle.

Build:
    pyinstaller wuggy.spec

Output:
    dist/Wuggy.app  (macOS app bundle)
"""

import os

# All official language plugin module names
LANGUAGE_PLUGINS = [
    'orthographic_basque',
    'orthographic_dutch',
    'orthographic_english',
    'orthographic_french',
    'orthographic_german',
    'orthographic_italian',
    'orthographic_polish',
    'orthographic_serbian_cyrillic',
    'orthographic_serbian_latin',
    'orthographic_spanish',
    'orthographic_vietnamese',
    'phonetic_english_celex',
    'phonetic_english_cmu',
    'phonetic_french',
    'phonetic_italian',
]

# Hidden imports: language plugins are loaded dynamically via importlib
hidden_imports = [
    'wuggy',
    'wuggy.generators',
    'wuggy.generators.wuggygenerator',
    'wuggy.plugins',
    'wuggy.plugins.baselanguageplugin',
    'wuggy.plugins.language_data',
    'wuggy.evaluators',
    'wuggy.evaluators.ld1nn',
    'wuggy.utilities',
    'wuggy.utilities.bigramchain',
    # Flask internals not always auto-detected
    'flask',
    'jinja2',
    'werkzeug',
    'werkzeug.serving',
    'werkzeug.routing',
    'click',
] + [
    f'wuggy.plugins.language_data.{name}.{name}'
    for name in LANGUAGE_PLUGINS
]

# Data files: templates, static assets, and all language data
datas = [
    ('wuggy/gui/templates', 'wuggy/gui/templates'),
    ('wuggy/gui/static',    'wuggy/gui/static'),
    ('wuggy/plugins/language_data', 'wuggy/plugins/language_data'),
]

a = Analysis(
    ['run_gui.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'PIL', 'PyQt5', 'PyQt6',
        'PySide2', 'PySide6', 'wx', 'gi',
        # statsmodels is only used by the ld1nn evaluator, which is not
        # part of the GUI workflow. Excluding it (and its scipy/pandas deps)
        # saves ~75MB in the app bundle.
        'statsmodels', 'scipy', 'pandas', 'patsy',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Wuggy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # no terminal window
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Wuggy',
)

if os.sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='Wuggy.app',
        icon='assets/wuggy.icns',
        bundle_identifier='org.wuggycode.wuggy',
        info_plist={
            'CFBundleDisplayName': 'Wuggy',
            'CFBundleShortVersionString': '1.2.0',
            'NSHighResolutionCapable': True,
            'NSRequiresAquaSystemAppearance': False,  # allow dark mode
        },
    )
