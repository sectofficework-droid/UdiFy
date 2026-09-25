"""PyInstaller entry point — thin wrapper around src.app.main.main().

A top-level script (rather than `python -m src.app.main`) is what
PyInstaller's Analysis expects as its script argument.
"""

from src.app.main import main

if __name__ == "__main__":
    raise SystemExit(main())
