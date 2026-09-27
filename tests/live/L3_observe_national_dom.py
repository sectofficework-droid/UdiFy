r"""L3 — observe the REAL National UDISE+ DOM, without submitting anything.

This is the script that replaces guessing from a screen recording. It drives
the real portal in a visible browser, walks the confirmed navigation chain,
and **dumps the actual DOM structure** of each screen so the adapter's
selectors can be checked against reality rather than against a video.

    .venv\Scripts\python.exe tests\live\L3_observe_national_dom.py

SAFETY — read this before running:

- **Nothing is ever submitted.** The script clicks navigation links and
  opens the Add Student form, then stops. It does not click Save, Submit,
  Confirm, or any button that would create or change a government record.
  The final screen is reached but not confirmed.
- **One session.** It logs in once and reuses that session. Do not re-run
  in a loop: repeated logins against a government portal can trip fraud
  detection and get the school's real account flagged or locked.
- **A CAPTCHA is expected.** Type it into the browser window when prompted.
- **You are expected to watch.** A visible browser opens and stays open.

Output: a directory of text dumps under `diagnostics/l3_observation/`
(each screen's inputs, buttons, labels and headings) plus a summary printed
to the console. No credentials are ever written to those files.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from _live_common import banner, require_live_settings, show_config_summary

from playwright.sync_api import sync_playwright

from src.portals.base import AutomationPausedForUser
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter

OUT_DIR = Path(__file__).resolve().parents[2] / "diagnostics" / "l3_observation"

# Controls whose text indicates they would COMMIT a change. Used to FLAG
# such controls in the dump so they are obvious during review, and as a
# tripwire if this walk is ever extended. It is not the primary safety
# mechanism: the script only ever calls the adapter's known *navigation*
# methods (login, Students Module, academic year, dismiss notifications,
# open Add Student) and none of those submits a form. The real guarantee is
# that no save/submit/confirm call appears anywhere below.
DANGEROUS_TEXT = re.compile(
    r"^\s*(save|submit|confirm|create|add new student|finali[sz]e|proceed|yes)\b",
    re.IGNORECASE,
)


def _dump(page, name: str) -> None:
    """Write the page's interactive structure to a text file.

    Only *structure* is captured — tag, type, id, name, placeholder and
    visible label text. No input `value` is recorded, because a logged-in
    government page can have identity values pre-filled in fields and this
    dump is written to disk.
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = page.evaluate(
        """() => {
        const vis = el => {
          const r = el.getBoundingClientRect();
          const s = getComputedStyle(el);
          return r.width > 0 && r.height > 0 && s.visibility !== 'hidden'
                 && s.display !== 'none';
        };
        const labelOf = el => {
          if (el.id) {
            const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
            if (l) return l.innerText.trim();
          }
          const p = el.closest('label');
          if (p) return p.innerText.trim();
          const ph = el.getAttribute('placeholder');
          if (ph) return ph;
          const ao = el.getAttribute('aria-label');
          if (ao) return ao;
          return '';
        };
        const inputs = [...document.querySelectorAll('input, select, textarea')]
          .filter(vis).map(el => ({
            tag: el.tagName.toLowerCase(),
            type: el.getAttribute('type') || '',
            id: el.id || '',
            name: el.getAttribute('name') || '',
            label: labelOf(el),
            required: el.required === true,
          }));
        const buttons = [...document.querySelectorAll('button, [role=button], a.btn, input[type=submit]')]
          .filter(vis).map(el => ({
            tag: el.tagName.toLowerCase(),
            text: (el.innerText || el.value || '').trim().slice(0, 80),
            id: el.id || '',
            cls: (el.className && typeof el.className === 'string')
                   ? el.className.slice(0, 60) : '',
          }));
        const tabs = [...document.querySelectorAll('[role=tab], .nav-link, .tab')]
          .filter(vis).map(el => (el.innerText || '').trim().slice(0, 60)).filter(Boolean);
        const headings = [...document.querySelectorAll('h1,h2,h3,h4,h5')]
          .filter(vis).map(el => el.innerText.trim().slice(0, 100)).filter(Boolean);
        const modals = [...document.querySelectorAll('.modal, [role=dialog], .modal-dialog')]
          .filter(vis).map(el => (el.innerText || '').trim().slice(0, 200));
        return { url: location.href, title: document.title,
                 inputs, buttons, tabs, headings, modals };
    }"""
    )
    path = OUT_DIR / f"{name}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n  --- {name} ---")
    print(f"  url    : {data['url']}")
    print(f"  title  : {data['title']}")
    print(f"  inputs : {len(data['inputs'])}")
    for item in data["inputs"][:40]:
        print(
            f"      <{item['tag']} type={item['type']!r} id={item['id']!r} "
            f"name={item['name']!r} label={item['label']!r}"
            + (" REQUIRED" if item["required"] else "")
            + ">"
        )
    print(f"  buttons: {len(data['buttons'])}")
    for item in data["buttons"][:30]:
        flag = "  <-- WOULD COMMIT" if DANGEROUS_TEXT.match(item["text"]) else ""
        print(f"      [{item['tag']}] {item['text']!r} id={item['id']!r}{flag}")
    if data["tabs"]:
        print(f"  tabs   : {data['tabs']}")
    if data["headings"]:
        print(f"  heads  : {data['headings'][:10]}")
    for modal in data["modals"][:3]:
        print(f"  MODAL  : {modal!r}")
    return data


def _prompt(message: str) -> str:
    """Ask the operator for input, failing clearly if there is no console.

    This script is interactive by necessity: the CAPTCHA on a government
    portal can only be solved by a person looking at the browser window,
    and the class name for the Add Student row is a judgement call. If it
    is run with no interactive console (piped, or a scheduler), say so
    plainly instead of dying on a bare EOFError.
    """
    try:
        return input(message).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise SystemExit(
            "\nThis script needs an interactive console: it pauses for you to "
            "type the CAPTCHA into the browser window and to choose a class "
            "name.\n\n"
            "Run it from your own terminal so you can see and type:\n"
            "    .venv\\Scripts\\python.exe tests\\live\\L3_observe_national_dom.py\n\n"
            "The login-page DOM dump was still written before this point, so "
            f"check {OUT_DIR} for what was captured."
        )


def _login(adapter: NationalUDISEPortalAdapter, settings) -> None:
    for attempt in (1, 2):
        try:
            adapter.login(
                settings.national_portal.username,
                settings.national_portal.password,
            )
            return
        except AutomationPausedForUser as exc:
            if attempt == 2:
                raise SystemExit(f"CAPTCHA still unresolved: {exc}")
            print(f"\n  CAPTCHA encountered ({exc}).")
            print("  Type it into the visible browser window, then press Enter here.")
            _prompt("  ... ")


def main() -> int:
    settings = require_live_settings()
    show_config_summary(settings)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    print(f"Observation dumps will be written to:\n  {OUT_DIR}")

    banner("L3 — real National UDISE+ DOM observation (READ-ONLY)")
    print("Watch the browser window. Nothing will be submitted.")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        try:
            page = browser.new_page()
            print("\n[1/6] opening the National UDISE+ login page...")
            page.goto(settings.national_portal.login_url)
            _dump(page, f"{stamp}_1_login")

            print("\n[2/6] logging in (one attempt; captcha handled if prompted)...")
            adapter = NationalUDISEPortalAdapter(page, timeout_ms=60_000)
            _login(adapter, settings)
            print(f"  logged in -> {page.url}")
            _dump(page, f"{stamp}_2_post_login")

            print("\n[3/6] Students Module...")
            adapter.open_students_module()
            print(f"  -> {page.url}")
            _dump(page, f"{stamp}_3_after_students_module")

            print("\n[4/6] academic year choice...")
            adapter.choose_current_academic_year()
            print(f"  -> {page.url}")
            school = _dump(page, f"{stamp}_4_school_dashboard")

            print("\n[5/6] notification modals...")
            adapter.dismiss_pending_notifications()
            _dump(page, f"{stamp}_5_after_notifications")

            banner("L3 — class rows on the School Dashboard")
            rows = page.evaluate(
                """() => [...document.querySelectorAll('table tr')].map(tr => {
                    const cells = [...tr.querySelectorAll('td')]
                        .map(td => td.innerText.trim()).filter(Boolean);
                    return cells.join(' | ');
                }).filter(Boolean)"""
            )
            for index, row in enumerate(rows[:40]):
                print(f"   row {index}: {row}")
            print()
            print("  The adapter matches a class row by class name AND filters by")
            print("  section, because live evidence showed Section is 'A' for every")
            print("  class at this school. Compare the class-name column above with")
            print("  what open_add_student() expects.")

            banner("L3 — Add Student form (opened, NOT submitted)")
            print("  If the next step needs a class name, press Enter to skip it.")
            class_name = _prompt("  class name to use (blank = stop here): ")
            if not class_name:
                print("  Stopped before opening the form. Nothing was submitted.")
                return 0

            from src.engine.field_mapping import pen_row_to_new_student_init

            init = pen_row_to_new_student_init(
                {"Name of Student as per Aadhar Card": "OBSERVATION ONLY"},
                class_name=class_name,
                section="A",
            )
            adapter.open_add_student(init)
            print(f"  -> {page.url}")
            form = _dump(page, f"{stamp}_6_add_student_form")

            banner("L3 — what this proves")
            print(f"  navigation chain reached the Add Student form: {bool(form['inputs'])}")
            print(f"  fields on the form: {len(form['inputs'])}")
            print("\n  STOPPING HERE. The form was opened but NOT submitted.")
            print("  Compare the dumped field list against fill_identity_fields()")
            print("  and confirm_identity_details() in the adapter.")
            return 0
        finally:
            _prompt("\nPress Enter to close the browser (or Ctrl+C to force quit)... ")
            browser.close()


if __name__ == "__main__":
    raise SystemExit(main())
