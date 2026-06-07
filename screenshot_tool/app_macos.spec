# -*- mode: python ; coding: utf-8 -*-
import os
import rapidocr_onnxruntime

rapidocr_path = os.path.dirname(rapidocr_onnxruntime.__file__)
icon_icns = os.path.abspath('icon.icns')
if not os.path.exists(icon_icns):
    icon_icns = None
target_arch = os.environ.get('PYI_TARGET_ARCH') or None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('core', 'core'),
        ('tools', 'tools'),
        ('ui', 'ui'),
        ('locales', 'locales'),
        ('icon.png', '.'),
        (rapidocr_path, 'rapidocr_onnxruntime'),
    ],
    hiddenimports=[
        'PySide6.QtPrintSupport',
        'rapidocr_onnxruntime',
        'onnxruntime',
    ],
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
    [],
    exclude_binaries=True,
    name='截图贴图工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=target_arch,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_icns,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='截图贴图工具',
)

app = BUNDLE(
    coll,
    name='截图贴图工具.app',
    icon=icon_icns,
    bundle_identifier='com.kunqiong.screenshottool',
)
