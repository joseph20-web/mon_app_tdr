# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ICON_FILE = str(BASE_DIR / "assets" / "app.ico")
SPLASH_FILE = str(BASE_DIR / "assets" / "splash.png")
VERSION_FILE = str(BASE_DIR / "version.txt")

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['webview'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
splash = Splash(
    SPLASH_FILE,
    binaries=a.binaries,
    datas=a.datas,
)

exe = EXE(
    pyz,
    a.scripts,
    splash,
    a.binaries,
    a.datas,
    [],
    name='launcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    icon=ICON_FILE,
    version=VERSION_FILE,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
