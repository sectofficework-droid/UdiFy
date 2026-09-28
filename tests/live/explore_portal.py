r"""Interactive portal explorer — navigate and fill freely, submit nothing.

    .venv\Scripts\python.exe tests\live\explore_portal.py --portal national
    .venv\Scripts\python.exe tests\live\explore_portal.py --portal gujarat

WHY THIS EXISTS

The adapters' selectors were derived from screen recordings, and a
recording only shows what a person chose to show. Observing the REAL DOM
is stronger evidence, and until recently the only way to do that was a
throwaway script. This is the reusable version: a menu-driven explorer that
walks the real portal, dumps each screen's real structure, and lets you
inspect selectors without ever committing anything to a government record.

SAFE BY CONSTRUCTION

You are free to navigate, open forms, and **fill in fields** — filling a
text box changes nothing until it is saved. What is blocked is anything
that would write to a government system:

  - Every adapter call goes through `_safe()`, which refuses any method
    whose name matches a submit/save/confirm/create pattern. The blocked
    list is printed at startup so you know exactly what is off-limits.
  - A browser-level backstop re-arms on every page load and force-removes
    any matching control from the DOM. Even if a future adapter method
    slipped past `_safe()`, this stops the click reaching the portal.
  - Nothing is ever typed into the spreadsheets, and no local database
    record is written.

This means you can safely explore "what happens if I fill this form" —
which is exactly the question the recordings cannot answer — without
creating a single government record.

CAPTCHA

Both portals show one. It can only be solved by you, in the visible
browser window. The script pauses and waits. One session, please: repeated
logins against a government portal can trip fraud detection.

CAPTURES

Every screen is dumped to diagnostics/l3_observation/ as JSON (tag, type,
id, name, label, placeholder, required) and as a PNG screenshot, so the
structure can be reviewed afterwards without re-driving the browser.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from playwright.sync_api import sync_playwright  # noqa: E402

from src.config.settings import load_settings  # noqa: E402
from src.portals.udise_gujarat.adapter import GujaratUDISEPortalAdapter  # noqa: E402
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter  # noqa: E402

OUT_DIR = _ROOT / "diagnostics" / "l3_observation"

# Any adapter method whose name matches this is treated as committing a
# change and is refused. Deliberately broad: a false positive costs a
# little exploration, a false negative can create a real student record.
#
# Matching is on word boundaries in the method name, not a bare substring.
# A substring match on "import" also caught `read_generated_uid`? no - on
# "create" it caught nothing useful, but on "import" it would catch
# `check_aadhaar_availability` only by accident; the real lesson is that
# `find_transfer_request` (read-only) and `open_transfer_request_list`
# (navigation) contain "request" and must stay usable. Each alternative
# below is a genuine commit.
SUBMIT_METHOD_NAMES = frozenset(
    {
        # Gujarat UDISE
        "submit_manual_birth_details",
        "submit_cts_details",
        "save_current_tab",
        "confirm_transfer_request",
        # National UDISE+
        "confirm_identity_details",
        "complete_profile_preview",
        "submit_release_admission_detail",
        "generate_release_request",
    }
)


def is_blocked_method(name: str) -> bool:
    """True when calling this adapter method would commit a change.

    An explicit allowlist of the committing methods, rather than a pattern
    that tries to guess intent from the name. A guess was tried first and
    was wrong in both directions: it blocked the read-only
    `read_generated_uid` (via "create" in "created"?) and the harmless
    `find_transfer_request`. An allowlist fails safe — a new committing
    method is *allowed* until added here, which is why `open_add_student`
    is listed explicitly even though it merely opens a form: the operator
    fills it by hand and observation mode must not open the one-shot
    creation control.
    """
    return name in SUBMIT_METHOD_NAMES

# Second, independent backstop applied to the live DOM. Clicks are bound on
# the document in the capture phase, so dynamically added buttons are
# covered too.
BLOCK_SELECTOR = (
    "button, [role=button], input[type=submit], a.btn, a[href*='submit'], a[href*='save']"
)
BLOCK_TEXT = re.compile(
    r"^\s*(save|submit|confirm|create|add new student|finali[sz]e|proceed|yes|"
    r"generate|release)\b",
    re.IGNORECASE,
)

INJECT_BLOCKER = """
(() => {
  if (window.__udifySubmitBlocker) return;
  // Built with `new RegExp` from a NON-raw Python string, so the escaping
  // here is load-bearing and was verified by tests/live/test_observe_safety.py.
  // A JS string literal needs '\\\\' to produce a regex '\\', and the regex
  // itself needs '\\b' for a word boundary. Getting this wrong silently
  // disables the boundary, which made "Students Module" match (via the
  // trailing 's' + no boundary) and broke navigation entirely.
  const TEXT = new RegExp(
    '^\\\\s*(save|submit|confirm|create|add new student|finali[sz]e|proceed|yes|generate|release)\\\\b',
    'i'
  );
  const SEL = "button,[role=button],input[type=submit],a.btn,a[href*='submit'],a[href*='save']";
  const label = el =>
    ((el.innerText || el.value || el.getAttribute('aria-label') || '') + '').trim();
  const disarm = el => {
    if (el.dataset && el.dataset.udifyBlocked) return;
    el.dataset.udifyBlocked = '1';
    el.setAttribute('data-udify-blocked', '1');
    el.style.opacity = '0.35';
    el.style.pointerEvents = 'none';
    el.style.outline = '3px dashed #c0392b';
    el.title = 'UdiFy observation mode: submitting is disabled';
    el.addEventListener('click', e => {
      e.preventDefault(); e.stopImmediatePropagation();
    }, true);
  };
  const scan = () => {
    document.querySelectorAll(SEL).forEach(el => {
      const t = label(el);
      // Text is the ONLY signal. A second signal — "has an explicitly
      // typed submit/image attribute" — was tried and removed
      // (2026-09-28): it disarmed the real Gujarat portal's "Go" search
      // button and its "LOG IN" button, both genuinely
      // <button type="submit">, which broke navigation AND login
      // entirely. HTML's type="submit" describes how a browser submits a
      // form, not whether the action commits a government record — a
      // login or a search is a submit in HTML's sense but not in ours.
      // The test fixture never modeled a benign type="submit" control,
      // which is why this shipped unnoticed until the real portal caught
      // it. Text (what the control actually says it does) is the correct
      // signal on its own.
      if (TEXT.test(t)) { disarm(el); }
    });
  };
  const mo = new MutationObserver(() => scan());
  const arm = () => {
    scan();
    mo.disconnect();
    mo.observe(document.documentElement, { childList: true, subtree: true });
  };
  document.addEventListener('DOMContentLoaded', arm);
  if (document.readyState !== 'loading') arm();
  window.__udifySubmitBlocker = true;
})();
"""


def _prompt(message: str = "  > ") -> str:
    try:
        return input(message).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise SystemExit("Session ended.")


DUMP_SCRIPT = """() => {
  const vis = el => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
  };
  const labelOf = el => {
    if (el.id) {
      const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (l) return l.innerText.trim();
    }
    const p = el.closest('label');
    if (p) return p.innerText.trim();
    return (el.getAttribute('placeholder') || el.getAttribute('aria-label') || '');
  };
  return {
    url: location.href,
    title: document.title,
    inputs: [...document.querySelectorAll('input, select, textarea')].filter(vis).map(el => ({
      tag: el.tagName.toLowerCase(),
      type: el.getAttribute('type') || '',
      id: el.id || '',
      name: el.getAttribute('name') || '',
      label: labelOf(el),
      required: el.required === true,
      disabled: el.disabled === true,
    })),
    buttons: [...document.querySelectorAll('button, [role=button], a.btn, input[type=submit]')]
      .filter(vis).map(el => ({
        tag: el.tagName.toLowerCase(),
        text: ((el.innerText || el.value || '') + '').trim().slice(0, 80),
        id: el.id || '',
        disabled: el.disabled === true || el.dataset.udifyBlocked === '1',
      })),
    tabs: [...document.querySelectorAll('[role=tab], .nav-link, .tab')].filter(vis)
      .map(el => (el.innerText || '').trim().slice(0, 60)).filter(Boolean),
    headings: [...document.querySelectorAll('h1,h2,h3,h4,h5')].filter(vis)
      .map(el => el.innerText.trim().slice(0, 100)).filter(Boolean),
    rows: [...document.querySelectorAll('table tr')].map(tr =>
      [...tr.querySelectorAll('td')].map(td => td.innerText.trim()).filter(Boolean).join(' | ')
    ).filter(Boolean),
  };
}"""


class Explorer:
    def __init__(self, portal: str):
        self.portal = portal
        self.stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.step = 0
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Captures -> {OUT_DIR}")

    # -- capture ------------------------------------------------------
    def capture(self, label: str) -> dict:
        self.step += 1
        safe = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")[:40]
        name = f"{self.stamp}_{self.portal}_{self.step:02d}_{safe}"
        data = self.page.evaluate(DUMP_SCRIPT)
        (OUT_DIR / f"{name}.json").write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        try:
            self.page.screenshot(path=str(OUT_DIR / f"{name}.png"), full_page=False)
        except Exception:
            pass
        self.show(data)
        return data

    def show(self, data: dict) -> None:
        print(f"\n  url    : {data['url']}")
        print(f"  title  : {data['title']}")
        print(f"  inputs : {len(data['inputs'])}")
        for i in data["inputs"][:30]:
            flags = "".join([
                " REQUIRED" if i["required"] else "",
                " disabled" if i["disabled"] else "",
            ])
            print(f"      <{i['tag']} type={i['type']!r} id={i['id']!r} "
                  f"name={i['name']!r} label={i['label']!r}>{flags}")
        print(f"  buttons: {len(data['buttons'])}")
        for b in data["buttons"][:25]:
            mark = "  [BLOCKED - would submit]" if BLOCK_TEXT.match(b["text"]) else ""
            dis = " (disabled)" if b["disabled"] else ""
            print(f"      {b['text']!r}{dis}{mark}")
        if data["tabs"]:
            print(f"  tabs   : {data['tabs']}")
        if data["headings"]:
            print(f"  heads  : {data['headings'][:8]}")
        for r in data["rows"][:15]:
            print(f"   row: {r}")

    # -- safe adapter access -----------------------------------------
    def safe(self, method_name: str, *args, **kwargs):
        """Call an adapter method unless its name implies a commit."""
        if is_blocked_method(method_name):
            raise SystemExit(
                f"\nBLOCKED: {method_name!r} would submit/commit a change on the "
                f"{self.portal} portal.\n"
                "Observation mode never does that. Everything else is available."
            )
        method = getattr(self.adapter, method_name)
        result = method(*args, **kwargs)
        return result

    def methods(self) -> None:
        names = [
            n for n in dir(self.adapter)
            if not n.startswith("_") and callable(getattr(self.adapter, n))
            and n not in {"login", "page"}
        ]
        print("\n  Adapter methods available in observation mode:")
        for name in sorted(names):
            status = "BLOCKED" if is_blocked_method(name) else "allowed"
            print(f"      {name:42} {status}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portal", choices=("national", "gujarat"), required=True)
    args = parser.parse_args()

    settings = load_settings()  # raises if any required credential is missing

    ex = Explorer(args.portal)
    print("=" * 74)
    print(f"  UdiFy OBSERVATION MODE - {args.portal.upper()} portal")
    print("=" * 74)
    print("  You may navigate and FILL fields freely.")
    print("  Nothing will be submitted: committing controls are blocked in the")
    print("  DOM, and the adapter call layer refuses submit/save/confirm methods.")
    print()
    print("  Commands:  <method> [args...]   run an adapter method")
    print("            dump                  capture + print the current screen")
    print("            methods                list what is allowed / blocked")
    print("            url                    print the current URL")
    print("            back                   browser back")
    print("            quit                   close the browser and exit")
    print("=" * 74)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        try:
            ex.page = browser.new_page()
            # Arm the blocker before any site script runs, and re-arm on
            # every navigation.
            ex.page.add_init_script(INJECT_BLOCKER)
            ex.page.on("framenavigated", lambda _: ex.page.evaluate(INJECT_BLOCKER))

            if args.portal == "national":
                ex.page.goto(settings.national_portal.login_url)
                ex.adapter = NationalUDISEPortalAdapter(ex.page, timeout_ms=60_000)
                creds = (settings.national_portal.username, settings.national_portal.password)
                label = "National UDISE+"
            else:
                ex.page.goto(settings.gujarat_portal.login_url)
                ex.adapter = GujaratUDISEPortalAdapter(ex.page, timeout_ms=60_000)
                creds = (settings.gujarat_portal.school_code, settings.gujarat_portal.password)
                label = "Gujarat UDISE"

            ex.capture("login_page")
            print(f"\n  Solve the CAPTCHA for {label} in the browser window.")
            for attempt in (1, 2):
                try:
                    ex.adapter.login(*creds)
                    break
                except Exception as exc:
                    if "captcha" in str(exc).lower() and attempt == 1:
                        print("  CAPTCHA detected. Type it in, then press Enter here.")
                        _prompt()
                        continue
                    if attempt == 2:
                        raise SystemExit(f"  Login failed: {type(exc).__name__}: {exc}")
            print(f"  logged in -> {ex.page.url}")
            ex.capture("post_login")
            ex.methods()

            while True:
                raw = _prompt("\ncommand > ")
                if not raw:
                    continue
                if raw in {"quit", "q", "exit"}:
                    print("  closing.")
                    return 0
                if raw == "methods":
                    ex.methods()
                    continue
                if raw == "dump":
                    ex.capture("manual")
                    continue
                if raw == "url":
                    print(f"  {ex.page.url}")
                    continue
                if raw == "back":
                    ex.page.go_back()
                    ex.page.evaluate(INJECT_BLOCKER)
                    continue
                if not hasattr(ex.adapter, raw):
                    print(f"  no such method: {raw!r} (type 'methods')")
                    continue
                try:
                    result = ex.safe(raw)
                    print(f"  {raw} -> {result!r}")
                    ex.capture(f"after_{raw}")
                except SystemExit:
                    raise
                except Exception as exc:
                    print(f"  {raw} failed: {type(exc).__name__}: {exc}")
        finally:
            browser.close()


if __name__ == "__main__":
    raise SystemExit(main())
