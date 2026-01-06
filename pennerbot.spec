# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for PennerBot

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os

block_cipher = None

# Collect all data files
datas = [
    ('web/dist', 'web/dist'),  # Frontend build
    ('src', 'src'),  # Source code modules
    ('server.py', '.'),  # Server module (needed for direct import in bundle mode)
    ('gui_launcher.py', '.'),  # GUI launcher module
    ('web/serve.py', 'web'),  # Web server module
]

# Collect all hidden imports (modules loaded dynamically)
hiddenimports = [
    # Uvicorn (minimal)
    'uvicorn.logging',
    'uvicorn.loops.auto',
    'uvicorn.loops.uvloop',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.websockets.wsproto',
    'uvicorn.lifespan.on',
    # FastAPI
    'fastapi',
    'starlette',
    'starlette.routing',
    'starlette.responses',
    'starlette.middleware',
    'starlette.middleware.cors',
    # Aiohttp (minimal)
    'aiohttp',
    'aiohttp.web',
    'aiohttp.typedefs',
    # Web scraping
    'bs4',
    'bs4.builder',
    'lxml.etree',
    # Database
    'sqlalchemy',
    'sqlalchemy.ext.declarative',
    'sqlalchemy.orm',
    'sqlalchemy.orm.decl_api',
    # HTTP client
    'httpx',
    'httpx._api',
    # Scheduler
    'apscheduler.schedulers.asyncio',
    # GUI components
    'tkinter.ttk',
    'pystray',
    'PIL.Image',
    'PIL.ImageDraw',
    # Process management
    'psutil',
    # Event loop
    'asyncio',
    'asyncio.base_events',
]

# Exclude unnecessary modules to reduce size
excludes = [
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
    ['gui_launcher.py'],
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
    console=False,  # Set to False to hide console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='web/public/favicon.ico',  # Add icon if you have one
)
