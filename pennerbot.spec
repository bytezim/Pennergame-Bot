# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for PennerBot

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os

block_cipher = None

# Collect all data files
datas = [
    ('web/dist', 'web/dist'),  # Frontend build
    ('src', 'src'),  # Source code modules
]

# Collect all hidden imports (modules loaded dynamically)
hiddenimports = [
    # Uvicorn (minimal)
    'uvicorn.logging',
    'uvicorn.loops.auto',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan.on',
    # Aiohttp (minimal)
    'aiohttp',
    'aiohttp.web',
    # Web scraping
    'bs4',
    'lxml.etree',
    # Database
    'sqlalchemy',
    'sqlalchemy.ext.declarative',
    # HTTP client
    'httpx',
    # Scheduler
    'apscheduler.schedulers.asyncio',
]

# Exclude unnecessary modules to reduce size
excludes = [
    'tkinter',
    'unittest',
    'pydoc',
    'doctest',
    'test',
    'setuptools',
    'pip',
    'wheel',
    'numpy',
    'pandas',
    'matplotlib',
    'PIL',
    'IPython',
    'jupyter',
    'notebook',
    'scipy',
    'torch',
    'tensorflow',
]

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,  # Now excluding unnecessary modules
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=True,  # Better compression
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PennerBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # Strip symbols to reduce size
    upx=True,  # UPX compression enabled
    upx_exclude=[
        # Exclude system DLLs from UPX compression (prevents issues)
        'vcruntime*.dll',
        'msvcp*.dll',
        'python*.dll',
        'api-ms-win-*.dll',
    ],
    runtime_tmpdir=None,
    console=True,  # Set to False to hide console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='web/public/favicon.ico',  # Add icon if you have one
)
