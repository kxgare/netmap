# Build on Windows 10/11 with Python 3.12+, not by cross-compiling on Linux.
from pathlib import Path

root = Path(SPECPATH)
a = Analysis(
    [str(root / 'launch.py')],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / 'netmap' / 'resources'), 'netmap/resources')],
    hiddenimports=[],
    hookspath=[],
    excludes=['tkinter'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='NetMap',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(root / 'netmap' / 'resources' / 'logo.ico'),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='NetMap')
