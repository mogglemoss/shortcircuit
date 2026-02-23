# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

a = Analysis(
    ['/Users/scott/Documents/Devlopment Projects/Eve Online/shortcircuit/src/main.py'],
    pathex=['/Users/scott/Documents/Devlopment Projects/Eve Online/shortcircuit'],
    binaries=[],
    datas=[('/Users/scott/Documents/Devlopment Projects/Eve Online/shortcircuit/src/database', 'database')],
    hiddenimports=['shortcircuit', 'shortcircuit.app', 'shortcircuit.model', 'shortcircuit.model.esi', 'shortcircuit.model.esi.esi', 'shortcircuit.model.esi.server', 'shortcircuit.model.esi_processor', 'shortcircuit.model.evedb', 'shortcircuit.model.evescout', 'shortcircuit.model.logger', 'shortcircuit.model.mapper_registry', 'shortcircuit.model.navigation', 'shortcircuit.model.navprocessor', 'shortcircuit.model.pathfinder', 'shortcircuit.model.solarmap', 'shortcircuit.model.test_evedb', 'shortcircuit.model.test_pathfinder', 'shortcircuit.model.test_solarmap', 'shortcircuit.model.test_tripwire', 'shortcircuit.model.test_tripwire_gate', 'shortcircuit.model.test_wanderer', 'shortcircuit.model.tripwire', 'shortcircuit.model.utility', 'shortcircuit.model.utility.configuration', 'shortcircuit.model.utility.gui_about', 'shortcircuit.model.utility.gui_main', 'shortcircuit.model.utility.gui_tripwire', 'shortcircuit.model.utility.singleton', 'shortcircuit.model.versioncheck', 'shortcircuit.model.wanderer', 'shortcircuit.resources', 'httpx', 'dateutil', 'semver', 'qdarktheme', 'typing_extensions', 'appdirs'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6.QtQml', 'PySide6.QtQuick'],
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
    name='ShortCircuit',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False, 
    upx=True,
    console=False,  # Windowed mode
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch='x86_64',
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ShortCircuit',
)
