# -*- mode: python ; coding: utf-8 -*-
import os

icon_icns = os.path.abspath('icon.icns')
if not os.path.exists(icon_icns):
    icon_icns = None
target_arch = os.environ.get('PYI_TARGET_ARCH') or None

a = Analysis(
    ['updater.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('core', 'core'),
        ('locales', 'locales'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pywin32', 'win32api', 'win32con', 'win32gui', 'win32com', 'comtypes'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='updater',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=target_arch,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_icns,
)
