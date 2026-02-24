# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['/Users/scott/Documents/Devlopment Projects/Eve Online/daytripper/shortcircuit/src/main.py'],
    pathex=['/Users/scott/Documents/Devlopment Projects/Eve Online/daytripper/shortcircuit/src'],
    binaries=[],
    datas=[('/Users/scott/Documents/Devlopment Projects/Eve Online/daytripper/shortcircuit/src/database', 'database')],
    hiddenimports=['shortcircuit', 'shortcircuit.app', 'shortcircuit.model', 'shortcircuit.model.esi', 'shortcircuit.model.esi.esi', 'shortcircuit.model.esi.server', 'shortcircuit.model.esi_processor', 'shortcircuit.model.evedb', 'shortcircuit.model.evescout', 'shortcircuit.model.logger', 'shortcircuit.model.mapper_registry', 'shortcircuit.model.navigation', 'shortcircuit.model.navprocessor', 'shortcircuit.model.pathfinder', 'shortcircuit.model.solarmap', 'shortcircuit.model.test_evedb', 'shortcircuit.model.test_pathfinder', 'shortcircuit.model.test_solarmap', 'shortcircuit.model.test_tripwire', 'shortcircuit.model.test_tripwire_gate', 'shortcircuit.model.tripwire', 'shortcircuit.model.utility', 'shortcircuit.model.utility.configuration', 'shortcircuit.model.utility.gui_about', 'shortcircuit.model.utility.gui_main', 'shortcircuit.model.utility.gui_tripwire', 'shortcircuit.model.utility.singleton', 'shortcircuit.model.versioncheck', 'shortcircuit.model.wanderer', 'shortcircuit.resources', 'httpx', 'dateutil', 'semver', 'qdarktheme', 'typing_extensions', 'appdirs', 'shortcircuit.model.wanderer'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6.QtQml', 'PySide6.QtQuick'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

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
    console=False,
    disable_windowed_traceback=False,
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
    name='ShortCircuit',
)
app = BUNDLE(
    coll,
    name='ShortCircuit.app',
    icon=None,
    bundle_identifier=None,
)
