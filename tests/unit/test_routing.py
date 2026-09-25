"""Unit tests for src/engine/routing.py's class -> ID-track determination
(spec §12/§Z/§160/§233)."""

from __future__ import annotations

import pytest

from src.engine.routing import IdTrack, determine_id_track


@pytest.mark.parametrize("class_name", ["Balvatika", "JrKG", "SrKG", "1st"])
def test_satyam_school_id_classes(class_name):
    assert determine_id_track(class_name) == IdTrack.SATYAM_SCHOOL_ID


@pytest.mark.parametrize("class_name", ["2nd", "3rd", "LKG/KG1/PP2", "UKG/KG2/PP1", "10th"])
def test_block_id_classes(class_name):
    assert determine_id_track(class_name) == IdTrack.BLOCK_ID
