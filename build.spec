# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for Whisper Speech-to-Text Dictation Tool."""

import sys
from PyInstaller.utils.hooks import collect_submodules, get_module_file_attribute

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.yaml', '.'),
        ('models', 'models'),
    ],
    hiddenimports=[
        'pystray',
        'PIL',
        'whisper',
        'sounddevice',
        'soundfile',
        'numpy',
        'pyperclip',
        'keyboard',
        'yaml',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Whisper-Dictation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window - runs in background/system tray
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',  # Optional: add icon later
)
