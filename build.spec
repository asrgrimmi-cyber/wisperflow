# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for Wisper.

Builds a lightweight client exe. Transcription happens on the GPU
server — torch/whisper are NOT bundled (they'd add ~2GB and crash
on systems without the right CUDA DLLs).

The exe includes: PyQt5 UI, audio capture, hotkey, text injection,
HTTP client for GPU server, and the first-run wizard.
"""

import os

a = Analysis(
    ['src/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('config.yaml', '.'),
    ],
    hiddenimports=[
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'sounddevice',
        'soundfile',
        '_sounddevice_data',
        'numpy',
        'pyperclip',
        'keyboard',
        'yaml',
        'requests',
    ],
    excludes=[
        'torch',
        'whisper',
        'torchaudio',
        'torchvision',
        'tiktoken',
        'tiktoken_ext',
        'tensorboard',
        'matplotlib',
        'scipy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Wisper',
    debug=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,
    icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None,
)
