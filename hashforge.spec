# -*- mode: python ; coding: utf-8 -*-
"""Native windowed build; HASHFORGE_ONEFILE=1 enables single-file output."""

import os
from pathlib import Path
import sys

root = Path(SPECPATH)
onefile = os.environ.get('HASHFORGE_ONEFILE', '0') == '1'
a = Analysis(
    [str(root / 'main.py')],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / 'assets' / 'icon.ico'), 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtWebEngineCore',
              'PySide6.QtWebEngineWidgets', 'pytest', 'PIL'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, *([a.binaries, a.datas] if onefile else []), [],
    name='HashForge',
    exclude_binaries=not onefile,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(root / 'assets' / 'icon.ico') if sys.platform == 'win32' else None,
    version=str(root / 'assets' / 'version_info.txt') if sys.platform == 'win32' else None,
)
if not onefile:
    collection = COLLECT(
        exe, a.binaries, a.datas, strip=False, upx=False, name='HashForge',
    )
