"""Class -> ID-track routing (spec §12/§Z/§160/§233).

Data-driven, not scattered if/else through the codebase (spec §Z: "The
application must make routing data-driven and configurable rather than
hardcoding scattered if/else statements").
"""

from __future__ import annotations

from enum import Enum

SATYAM_SCHOOL_ID_CLASSES: frozenset[str] = frozenset(
    {"Balvatika", "JrKG", "SrKG", "1st"}
)


class IdTrack(str, Enum):
    SATYAM_SCHOOL_ID = "SATYAM_SCHOOL_ID"
    BLOCK_ID = "BLOCK_ID"


def determine_id_track(class_name: str) -> IdTrack:
    """spec §12: JrKG/SrKG/Balvatika/1st -> Satyam School ID; 2nd+ -> Block ID."""
    if class_name in SATYAM_SCHOOL_ID_CLASSES:
        return IdTrack.SATYAM_SCHOOL_ID
    return IdTrack.BLOCK_ID
