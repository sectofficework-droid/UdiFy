"""Small shared widgets used across screens (UI-SPEC.md §B.2 component
inventory: stat tiles, status chips)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

# Maps a business status/color word to the QSS chip[] property value.
_CHIP_KIND_BY_STATUS = {
    "GREEN": "green",
    "RESOLVED": "green",
    "LIGHT_ORANGE": "amber",
    "PENDING": "amber",
    "STILL_PENDING": "amber",
    "ACTION_REQUIRED": "amber",
    "MANUAL_REVIEW": "red",
    "STATUS_CHANGED": "red",
    "UNKNOWN_PORTAL_STATUS": "red",
    "UNRESOLVED_CLOSED": "red",
    "REOPENED": "navy",
    "VERIFYING": "navy",
    "RETRYING": "navy",
}


def status_chip(text: str, status_key: str | None = None) -> QLabel:
    """A small colored pill label. `status_key` selects the color (falls
    back to a lookup on `text` itself, then muted grey)."""
    kind = _CHIP_KIND_BY_STATUS.get((status_key or text).upper().replace(" ", "_"), "muted")
    chip = QLabel(text)
    chip.setProperty("chip", kind)
    return chip


def condition_chip(condition: int) -> QLabel:
    kinds = {1: "navy", 2: "teal", 3: "amber", 4: "plum"}
    chip = QLabel(f"Condition {condition}")
    chip.setProperty("chip", kinds.get(condition, "muted"))
    return chip


class StatTile(QFrame):
    def __init__(self, label: str, value: str = "0"):
        super().__init__()
        self.setObjectName("StatTile")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("StatValue")
        layout.addWidget(self.value_label)
        caption = QLabel(label)
        caption.setObjectName("StatLabel")
        layout.addWidget(caption)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


def screen_header(title: str, subtitle: str = "") -> QWidget:
    wrap = QWidget()
    layout = QVBoxLayout(wrap)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    title_label = QLabel(title)
    title_label.setObjectName("ScreenTitle")
    layout.addWidget(title_label)
    if subtitle:
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("ScreenSubtitle")
        subtitle_label.setWordWrap(True)
        layout.addWidget(subtitle_label)
    return wrap
