# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec — single-file variant of installer.spec.

Produces one self-contained UdiFy.exe (not a folder) at the repo root,
at the user's request (2026-09-26) for a single file they can hand off
or "install" directly, as opposed to installer.spec's one-folder build
under dist/UdiFy/.

Same bundled data as installer.spec (Playwright package data, the two
MOCK fixture pages) — see that file's docstring for why. This is a
genuine alternative packaging target, not a replacement: installer.spec
remains the documented one-folder build.

NOTE (2026-09-26): on this machine, NEITHER build launches without an
explicit Application Control / Smart App Control allowance — see
RELEASE-PLAN.md's "Build" section. A one-file build does not sidestep
that; it is exactly as unsigned as the one-folder build. This spec
exists to hand the user a single file to install/allow themselves, not
because one-file packaging solves the underlying block.

Build with: pyinstaller installer-onefile.spec
"""

from PyInstaller.utils.hooks import collect_data_files

playwright_datas = collect_data_files("playwright")

datas = playwright_datas + [
    ("tests/fixtures/gujarat_udise/new_entry.html", "fixtures/gujarat_udise"),
    ("tests/fixtures/udise_plus/new_pen_entry.html", "fixtures/udise_plus"),
]

a = Analysis(
    ["run_udify.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "openpyxl",
        "googleapiclient.discovery",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="UdiFy",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
