"""UdiFy entry point — thin wrapper around src.app.main.main().

Launched directly (`pythonw.exe run_udify.py`, the way the Start Menu
shortcut starts the app), `sys.path[0]` is this file's own directory, not
the project root — so `import src...` fails with ModuleNotFoundError.
Under `python.exe` that traceback is visible; under the **windowless
`pythonw.exe`, which is how the app is actually launched, there is no
console to show it**, so the process either dies silently or appears to
hang with no window. Only the test suite happened to work, because pytest
puts the rootdir on `sys.path` for us.

So the project root is put on `sys.path` explicitly, before importing
anything from the package. Cheap, and it makes the app launch correctly
however it is started.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.app.main import main  # noqa: E402  (must follow the sys.path setup)

if __name__ == "__main__":
    raise SystemExit(main())
