# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: one-folder, windowed, portable YARG Career Builder.

Build from the repository root with:

    pyinstaller packaging\\yarg_career_builder.spec

The resulting folder is written to ``dist\\YARG Career Builder\\`` and contains
the executable plus bundled Qt libraries. settings.json / sources.json are
created next to the executable on first run (seeded from the bundled defaults).
"""

import os

root = os.path.abspath(os.path.join(SPECPATH, ".."))

a = Analysis(
    [os.path.join(root, "packaging", "launcher.py")],
    pathex=[os.path.join(root, "src")],
    binaries=[],
    datas=[
        (os.path.join(root, "config", "settings.default.json"), "config"),
        (os.path.join(root, "config", "sources.default.json"), "config"),
        (os.path.join(root, "assets", "icon.png"), "assets"),
        (os.path.join(root, "templates", "Template.preset"), "templates"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Qt modules we never use — keeps the distributable small.
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngine",
        "PySide6.QtWebChannel",
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtQuickWidgets",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DRender",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
        "PySide6.QtNetwork",
        "PySide6.QtSql",
        "PySide6.QtTest",
        "PySide6.QtOpenGL",
        "PySide6.QtOpenGLWidgets",
        "PySide6.QtPrintSupport",
        "PySide6.QtSvg",
        "PySide6.QtXml",
        "tkinter",
        "pytest",
    ],
    noarchive=False,
    optimize=1,
    icon=os.path.join(root, "assets", "icon.ico"),
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="YARG Career Builder",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # windowed GUI (no console window)
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
    upx=False,
    upx_exclude=[],
    name="YARG Career Builder",
)
