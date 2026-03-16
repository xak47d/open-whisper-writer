# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for WhisperWriter.

Build with:
    pyinstaller whisper-writer.spec

Or use the build script:
    ./scripts/build.sh
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect data files from key packages
faster_whisper_data = collect_data_files('faster_whisper')
ctranslate2_data = collect_data_files('ctranslate2')

# Collect hidden imports that PyInstaller may miss
hidden_imports = [
    'faster_whisper',
    'ctranslate2',
    'huggingface_hub',
    'sounddevice',
    'soundfile',
    'webrtcvad',
    'pynput',
    'pynput.keyboard',
    'pynput.keyboard._xorg',
    'pynput.mouse',
    'pynput.mouse._xorg',
    'audioplayer',
    'yaml',
    'dotenv',
    'numpy',
    'onnxruntime',
    'tokenizers',
    'tiktoken',
    'tiktoken_ext',
    'tiktoken_ext.openai_public',
    'regex',
    'tqdm',
    'requests',
    'openai',
    'PIL',
]
hidden_imports += collect_submodules('pynput')
hidden_imports += collect_submodules('onnxruntime')

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('src/config_schema.yaml', 'src'),
    ] + faster_whisper_data + ctranslate2_data,
    hiddenimports=hidden_imports,
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'pandas',
        'jupyter',
        'notebook',
        'IPython',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='whisper-writer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/ww-logo.png',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='whisper-writer',
)
