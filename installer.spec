# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec — TODO.md step 16.

Bundles:
  - Playwright's package data (its own bundled PyInstaller hook,
    `playwright/_impl/__pyinstaller/hook-playwright.sync_api.py`,
    collects most of what's needed automatically; `collect_data_files`
    here is extra insurance for the `driver` directory specifically).
    This does NOT bundle a Chromium browser binary; the target machine
    still needs `playwright install chromium` run once (documented in
    SETUP-GUIDE.md) — matching how Playwright apps are normally
    distributed, since bundling a full browser build would make this a
    multi-hundred-MB installer for no benefit before the Live
    Verification Gate even runs.
  - The two MOCK fixture pages the GUI's Batch Queue/ND Reconciliation/
    Approval Monitoring screens drive in MOCK mode, so the packaged app's
    demo dataset keeps working (src/app/mock_fixtures.py resolves them
    via sys._MEIPASS when frozen).

Verified 2026-09-25: built with this spec, launched the resulting
dist/UdiFy/UdiFy.exe standalone, confirmed the GUI renders correctly and
its SQLite/diagnostics files are created — not just that the build step
exits 0.

Build with: pyinstaller installer.spec
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
    [],
    exclude_binaries=True,
    name="UdiFy",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
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
    upx=False,
    upx_exclude=[],
    name="UdiFy",
)
