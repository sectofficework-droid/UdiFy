r"""Persistent, code-driven portal session — one login, many actions.

`explore_portal.py` is a single process that blocks on `input()` for a
human to type each command. This is the alternative shape for when a
person wants to watch the browser while an agent (or a short script)
drives it: one process launches the browser and stays alive holding it
open; every subsequent action is a SEPARATE, short-lived process that
reconnects to that same already-open, already-logged-in browser over the
Chrome DevTools Protocol (CDP) and performs one action, then exits
without closing the browser. The login and the browser tab persist across
as many of those action calls as needed — no re-launch, no re-login.

Reuses `explore_portal.py`'s safety layer verbatim rather than a parallel
copy of it: the same `INJECT_BLOCKER` DOM-level backstop and the same
`is_blocked_method` submit-method allowlist. This is a different way to
DRIVE a session, not a different, looser safety model.

Usage (each a separate command, in the same terminal or different ones —
`start` blocks and must run in the background):

    .venv\Scripts\python.exe tests\live\session_control.py start --portal gujarat
    .venv\Scripts\python.exe tests\live\session_control.py login
    .venv\Scripts\python.exe tests\live\session_control.py act open_students_module
    .venv\Scripts\python.exe tests\live\session_control.py dump
    .venv\Scripts\python.exe tests\live\session_control.py methods
    .venv\Scripts\python.exe tests\live\session_control.py stop

CAPTCHA is unchanged from every other tool in this project: `login`
fills the credentials and raises if a CAPTCHA is present and unsolved.
Solve it by hand in the visible browser window, then run `login` again —
the same page is reused, so it picks up where it left off rather than
restarting.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from playwright.sync_api import sync_playwright  # noqa: E402

from src.config.settings import load_settings  # noqa: E402
from src.portals.base import AutomationPausedForUser  # noqa: E402
from src.portals.udise_gujarat.adapter import GujaratUDISEPortalAdapter  # noqa: E402
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter  # noqa: E402
from tests.live.explore_portal import (  # noqa: E402
    DUMP_SCRIPT,
    INJECT_BLOCKER,
    OUT_DIR,
    is_blocked_method,
)

# Fixed, single session at a time — matches the standing "one session,
# please" rule (repeated logins risk fraud-detection/lockout). Localhost
# only; Chromium's CDP listener does not accept remote connections by
# default, so this does not expose the session beyond this machine.
CDP_PORT = 9345
STATE_FILE = OUT_DIR / "session_control_state.json"


def _adapter_for(portal: str, page):
    if portal == "national":
        return NationalUDISEPortalAdapter(page, timeout_ms=60_000)
    return GujaratUDISEPortalAdapter(page, timeout_ms=60_000)


def _creds_for(portal: str, settings):
    if portal == "national":
        return (settings.national_portal.username, settings.national_portal.password)
    return (settings.gujarat_portal.school_code, settings.gujarat_portal.password)


def _login_url_for(portal: str, settings) -> str:
    if portal == "national":
        return settings.national_portal.login_url
    return settings.gujarat_portal.login_url


def _read_state() -> dict:
    if not STATE_FILE.exists():
        raise SystemExit(
            "No session is running. Start one first:\n"
            "  .venv\\Scripts\\python.exe tests\\live\\session_control.py start --portal gujarat"
        )
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def _connect_page():
    """Reconnect to the already-running browser over CDP.

    Deliberately never disconnects gracefully afterward — see `_finish()`.
    """
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp(f"http://localhost:{CDP_PORT}")
    context = browser.contexts[0]
    page = context.pages[0]
    return pw, page


def _finish(code: int) -> None:
    """End a connector command WITHOUT a graceful Playwright disconnect.

    Real bug found live (2026-09-28): calling `pw.stop()` (or letting the
    `sync_playwright()` `with` block exit normally) after
    `connect_over_cdp()` closed the actual page/tab on the persistent
    session — reproduced directly: `login()` correctly paused for a
    CAPTCHA, then the graceful-shutdown path on the way out closed the
    very page the operator needed to solve it on, even though the
    Chromium *process* itself stayed alive (`browser.contexts[0]` kept
    working; `context.pages[0]` came back empty). Every connector command
    here ends with this instead: flush output, then terminate the process
    at the OS level (`os._exit`), which skips Playwright's own
    disconnect/cleanup protocol messages entirely — nothing is sent to
    the remote browser on the way out, so the page it's showing cannot be
    affected by this process ending.
    """
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


def cmd_start(portal: str) -> int:
    settings = load_settings()  # raises if any required credential is missing
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False, args=[f"--remote-debugging-port={CDP_PORT}"]
        )
        page = browser.new_page()
        page.add_init_script(INJECT_BLOCKER)
        page.on("framenavigated", lambda _: page.evaluate(INJECT_BLOCKER))
        page.goto(_login_url_for(portal, settings))

        STATE_FILE.write_text(json.dumps({"portal": portal}), encoding="utf-8")
        print(f"Session started for {portal!r} on CDP port {CDP_PORT}.")
        print("Browser stays open. In another command, run:")
        print("  tests\\live\\session_control.py login")
        print("This process must keep running — do not close this window/process;")
        print("closing it closes the browser. Run 'stop' from elsewhere to end cleanly.")

        try:
            while STATE_FILE.exists():
                time.sleep(2)
        except KeyboardInterrupt:
            pass
        finally:
            browser.close()
            if STATE_FILE.exists():
                STATE_FILE.unlink()
    return 0


def cmd_stop() -> int:
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("Stop signal sent — the 'start' process will close the browser shortly.")
    else:
        print("No session state file found; nothing to stop.")
    return 0


def cmd_login() -> int:
    state = _read_state()
    portal = state["portal"]
    settings = load_settings()
    _pw, page = _connect_page()
    adapter = _adapter_for(portal, page)
    try:
        adapter.login(*_creds_for(portal, settings))
    except AutomationPausedForUser as exc:
        print(f"PAUSED: {exc}")
        print("Solve the CAPTCHA in the visible browser window, then run "
              "'login' again to continue from here.")
        _finish(1)
    print(f"Logged in -> {page.url}")
    _finish(0)


def cmd_act(method_name: str, args: list[str]) -> int:
    if is_blocked_method(method_name):
        raise SystemExit(
            f"BLOCKED: {method_name!r} would submit/commit a change on the real "
            "portal. This tool never does that."
        )
    state = _read_state()
    _pw, page = _connect_page()
    adapter = _adapter_for(state["portal"], page)
    if not hasattr(adapter, method_name):
        print(f"no such method: {method_name!r}")
        _finish(1)
    try:
        result = getattr(adapter, method_name)(*args)
    except Exception as exc:
        print(f"{method_name} failed: {type(exc).__name__}: {exc}")
        _finish(1)
    print(f"{method_name} -> {result!r}")
    _finish(0)


def cmd_dump(label: str) -> int:
    state = _read_state()
    _pw, page = _connect_page()
    from datetime import datetime
    import re

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")[:40] or "manual"
    name = f"{stamp}_{state['portal']}_{safe}"
    data = page.evaluate(DUMP_SCRIPT)
    (OUT_DIR / f"{name}.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    try:
        page.screenshot(path=str(OUT_DIR / f"{name}.png"), full_page=False)
    except Exception:
        pass
    print(f"url    : {data['url']}")
    print(f"title  : {data['title']}")
    print(f"inputs : {len(data['inputs'])}")
    for i in data["inputs"][:40]:
        print(f"    <{i['tag']} type={i['type']!r} id={i['id']!r} "
              f"name={i['name']!r} label={i['label']!r}>"
              f"{' REQUIRED' if i['required'] else ''}"
              f"{' disabled' if i['disabled'] else ''}")
    print(f"buttons: {len(data['buttons'])}")
    for b in data["buttons"][:30]:
        print(f"    {b['text']!r}{' (disabled)' if b['disabled'] else ''}")
    if data["tabs"]:
        print(f"tabs   : {data['tabs']}")
    if data["headings"]:
        print(f"heads  : {data['headings'][:8]}")
    print(f"saved  : {OUT_DIR / (name + '.json')}")
    _finish(0)


def cmd_methods() -> int:
    state = _read_state()
    _pw, page = _connect_page()
    adapter = _adapter_for(state["portal"], page)
    names = [
        n for n in dir(adapter)
        if not n.startswith("_") and callable(getattr(adapter, n))
        and n not in {"login", "page"}
    ]
    for name in sorted(names):
        print(f"    {name:42} {'BLOCKED' if is_blocked_method(name) else 'allowed'}")
    _finish(0)


def cmd_url() -> int:
    _read_state()
    _pw, page = _connect_page()
    print(page.url)
    _finish(0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="Launch the browser and keep it open.")
    p_start.add_argument("--portal", choices=("national", "gujarat"), required=True)

    sub.add_parser("stop", help="Close the running session's browser.")
    sub.add_parser("login", help="Attempt login on the running session.")
    sub.add_parser("methods", help="List allowed/blocked adapter methods.")
    sub.add_parser("url", help="Print the current page URL.")

    p_dump = sub.add_parser("dump", help="Capture the current screen's DOM + screenshot.")
    p_dump.add_argument("label", nargs="?", default="manual")

    p_act = sub.add_parser("act", help="Call one read-only/navigation adapter method.")
    p_act.add_argument("method")
    p_act.add_argument("args", nargs="*")

    args = parser.parse_args()

    if args.command == "start":
        return cmd_start(args.portal)
    if args.command == "stop":
        return cmd_stop()
    if args.command == "login":
        return cmd_login()
    if args.command == "methods":
        return cmd_methods()
    if args.command == "url":
        return cmd_url()
    if args.command == "dump":
        return cmd_dump(args.label)
    if args.command == "act":
        return cmd_act(args.method, args.args)
    raise SystemExit(f"unknown command: {args.command!r}")


if __name__ == "__main__":
    raise SystemExit(main())
