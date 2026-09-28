"""Qt stylesheet + brand palette (UI-SPEC.md §B.2).

Two-color brand system: navy (structural/official — sidebar, Condition 1,
informational callouts) + orange (action/attention — primary buttons,
focus rings, active nav accent). Semantic status colors (green/amber/red)
and categorical condition colors (teal/marigold/plum) stay separate from
the brand pair, functional-only, per the prototype's final iteration.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    ink: str
    paper: str
    surface: str
    surface_alt: str
    border: str
    navy: str
    navy_dark: str
    orange: str
    orange_dark: str
    green: str
    amber: str
    red: str
    teal: str
    plum: str
    muted: str


LIGHT = Palette(
    ink="#1C2321",
    paper="#EEF2EF",
    surface="#FFFFFF",
    surface_alt="#F5F7F6",
    border="#D6DCD9",
    navy="#0D2547",
    navy_dark="#081A33",
    orange="#A8460A",
    orange_dark="#7E3407",
    green="#256A42",
    amber="#8A5F16",
    red="#A23E3E",
    teal="#1F6F78",
    plum="#6B3E8C",
    muted="#5B6664",
)

DARK = Palette(
    ink="#EAEFEC",
    paper="#141917",
    surface="#1B211F",
    surface_alt="#202624",
    border="#333B38",
    navy="#5B84B8",
    navy_dark="#2A3F5A",
    orange="#E08A4F",
    orange_dark="#C06B34",
    green="#5FBE8A",
    amber="#D9A94C",
    red="#E08585",
    teal="#5FB8C2",
    plum="#B491D6",
    muted="#9BA6A2",
)


def build_stylesheet(p: Palette) -> str:
    return f"""
    QWidget {{
        background-color: {p.paper};
        color: {p.ink};
        font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
        font-size: 10.5pt;
    }}
    QMainWindow {{ background-color: {p.paper}; }}

    /* QWidget's own background-color above cascades to QLabel (a
       QWidget subclass) too, so every label painted its own solid
       {p.paper}-colored rectangle behind its text — visible as a grey
       "highlight" box around every single label wherever it sat on a
       different-colored parent (e.g. the white #Panel frames used
       throughout Settings/Dashboard). Labels should be transparent by
       default and let the parent's background show through; the chip/
       title labels below still win over this since attribute/ID
       selectors are more specific than this bare type selector. */
    QLabel {{ background: transparent; }}

    /* Qt's default dotted keyboard-focus rectangle reads as a stray,
       unstyled highlight against this theme — every other state
       (hover/checked/selection) already has its own deliberate styling,
       so the generic focus rect is redundant, not additive. */
    *:focus {{ outline: none; }}

    /* QScrollArea's viewport is an anonymous QWidget that does NOT
       automatically pick up the app-wide QWidget{{background-color}}
       rule above — it paints its own default background instead, which
       shows as a mismatched white/grey box behind the Settings form in
       dark mode specifically (the light palette happened to hide this
       by coincidence, since paper/surface are both near-white there).
       Targeting the scroll area itself and its content widget (the
       standard QSS pattern for this) fixes it in both themes. */
    QScrollArea {{ background: transparent; border: none; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}

    /* QSplitter's handle (diagnostics_view.py) renders as the OS's
       unstyled 3-dot grip by default — a jarring native-grey element
       against this theme in either mode. */
    QSplitter::handle {{
        background-color: {p.border};
    }}
    QSplitter::handle:horizontal {{ width: 2px; }}
    QSplitter::handle:vertical {{ height: 2px; }}

    /* QMessageBox (the "Confirm LIVE run" dialog, run_progress.py) is
       otherwise left to the OS's native dialog chrome, which looks
       inconsistent against this theme — white-on-dark or vice versa
       depending on the system theme, independent of which palette the
       app itself is using. */
    QMessageBox {{
        background-color: {p.surface};
    }}
    QMessageBox QLabel {{
        color: {p.ink};
        background: transparent;
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 12px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {p.border};
        border-radius: 5px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {p.muted}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

    QScrollBar:horizontal {{
        background: transparent;
        height: 12px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal {{
        background: {p.border};
        border-radius: 5px;
        min-width: 24px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {p.muted}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}

    QTableCornerButton::section {{
        background-color: {p.surface_alt};
        border: none;
        border-bottom: 1px solid {p.border};
    }}

    QComboBox {{
        selection-background-color: {p.orange};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 22px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {p.surface};
        border: 1px solid {p.border};
        selection-background-color: {p.orange};
        selection-color: #FFFFFF;
        outline: none;
    }}

    #Sidebar {{
        background-color: {p.navy};
        min-width: 220px;
        max-width: 220px;
    }}
    #Sidebar QLabel#BrandTitle {{
        color: #FFFFFF;
        font-family: "Source Serif 4", Georgia, serif;
        font-size: 15pt;
        font-weight: 600;
        padding: 18px 16px 14px 16px;
    }}
    #Sidebar QPushButton {{
        background: transparent;
        color: #DCE4EF;
        border: none;
        text-align: left;
        padding: 10px 16px;
        font-size: 10pt;
    }}
    #Sidebar QPushButton:hover {{
        background-color: rgba(255,255,255,0.08);
    }}
    #Sidebar QPushButton:checked {{
        background-color: rgba(255,255,255,0.12);
        border-left: 3px solid {p.orange};
        color: #FFFFFF;
        font-weight: 600;
    }}

    #ContentArea {{ background-color: {p.paper}; }}

    QLabel#ScreenTitle {{
        font-family: "Source Serif 4", Georgia, serif;
        font-size: 17pt;
        font-weight: 600;
        color: {p.ink};
        padding: 4px 0 2px 0;
    }}
    QLabel#ScreenSubtitle {{
        color: {p.muted};
        font-size: 9.5pt;
        padding-bottom: 10px;
    }}

    QFrame#Panel {{
        background-color: {p.surface};
        border: 1px solid {p.border};
        border-radius: 6px;
    }}
    QFrame#StatTile {{
        background-color: {p.surface};
        border: 1px solid {p.border};
        border-left: 4px solid {p.orange};
        border-radius: 4px;
    }}
    QLabel#StatValue {{
        font-family: "IBM Plex Mono", Consolas, monospace;
        font-size: 20pt;
        font-weight: 600;
    }}
    QLabel#StatLabel {{
        color: {p.muted};
        font-size: 9pt;
    }}

    QPushButton {{
        background-color: {p.orange};
        color: #FFFFFF;
        border: none;
        border-radius: 4px;
        padding: 7px 14px;
        font-weight: 600;
    }}
    QPushButton:hover {{ background-color: {p.orange_dark}; }}
    QPushButton:disabled {{ background-color: {p.border}; color: {p.muted}; }}
    QPushButton#Secondary {{
        background-color: {p.surface};
        color: {p.ink};
        border: 1px solid {p.border};
        font-weight: 500;
    }}
    QPushButton#Secondary:hover {{ background-color: {p.surface_alt}; }}

    QTableWidget {{
        background-color: {p.surface};
        gridline-color: {p.border};
        border: 1px solid {p.border};
        selection-background-color: {p.orange};
        selection-color: #FFFFFF;
    }}
    QHeaderView::section {{
        background-color: {p.surface_alt};
        color: {p.ink};
        padding: 6px;
        border: none;
        border-bottom: 1px solid {p.border};
        font-weight: 600;
    }}
    QTableWidget::item {{ padding: 4px; }}
    QTableWidget::item:focus {{ outline: none; }}

    QLineEdit, QComboBox, QPlainTextEdit {{
        background-color: {p.surface};
        border: 1px solid {p.border};
        border-radius: 4px;
        padding: 5px 8px;
    }}
    QLineEdit:focus, QComboBox:focus {{ border: 1px solid {p.orange}; }}

    QLabel.Mono {{
        font-family: "IBM Plex Mono", Consolas, monospace;
    }}

    QLabel[chip="green"] {{
        background-color: {p.green}; color: white; border-radius: 9px;
        padding: 2px 10px; font-size: 8.5pt; font-weight: 600;
    }}
    QLabel[chip="amber"] {{
        background-color: {p.amber}; color: white; border-radius: 9px;
        padding: 2px 10px; font-size: 8.5pt; font-weight: 600;
    }}
    QLabel[chip="red"] {{
        background-color: {p.red}; color: white; border-radius: 9px;
        padding: 2px 10px; font-size: 8.5pt; font-weight: 600;
    }}
    QLabel[chip="navy"] {{
        background-color: {p.navy}; color: white; border-radius: 9px;
        padding: 2px 10px; font-size: 8.5pt; font-weight: 600;
    }}
    QLabel[chip="teal"] {{
        background-color: {p.teal}; color: white; border-radius: 9px;
        padding: 2px 10px; font-size: 8.5pt; font-weight: 600;
    }}
    QLabel[chip="plum"] {{
        background-color: {p.plum}; color: white; border-radius: 9px;
        padding: 2px 10px; font-size: 8.5pt; font-weight: 600;
    }}
    QLabel[chip="muted"] {{
        background-color: {p.muted}; color: white; border-radius: 9px;
        padding: 2px 10px; font-size: 8.5pt; font-weight: 600;
    }}
    """
