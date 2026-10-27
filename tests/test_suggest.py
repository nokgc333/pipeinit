"""リネーム候補の提示(自動修正はしない、ADR-0003)のテスト。"""

from __future__ import annotations

import re

import pytest

from pipeinit.suggest import suggest_name

SHOT = re.compile(r"^SHOT\d{3}_[a-z]+_v\d{3}\.(hip|hiplc)$")
ASSET = re.compile(r"^[A-Z][A-Za-z0-9_]*\.(fbx|abc|usd)$")
PATTERNS = [SHOT, ASSET]


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("shot010_lighting_v003.hip", "SHOT010_lighting_v003.hip"),
        ("SHOT010_Lighting_v003.hip", "SHOT010_lighting_v003.hip"),
        ("SHOT010_lighting_v3.hip", "SHOT010_lighting_v003.hip"),
        ("SHOT10_lighting_v003.hip", "SHOT010_lighting_v003.hip"),
        ("SHOT010 lighting v003.hip", "SHOT010_lighting_v003.hip"),
        ("SHOT010-lighting-v003.hip", "SHOT010_lighting_v003.hip"),
        ("SHOT010_lighting_V003.hip", "SHOT010_lighting_v003.hip"),
        ("SHOT010_lighting_v003.HIP", "SHOT010_lighting_v003.hip"),
        ("character_hero.fbx", "Character_hero.fbx"),
        ("Character Hero.fbx", "Character_Hero.fbx"),
        ("shot10_Lighting_v3.HIP", "SHOT010_lighting_v003.hip"),
    ],
)
def test_common_mistakes_get_a_candidate_that_matches_a_pattern(name: str, expected: str) -> None:
    assert suggest_name(name, PATTERNS) == expected


def test_a_name_that_already_matches_gets_no_suggestion() -> None:
    assert suggest_name("SHOT010_lighting_v003.hip", PATTERNS) is None


@pytest.mark.parametrize("name", ["notes.txt", "x", "完全に違う名前.hip", "SHOT010.hip"])
def test_a_name_that_cannot_be_fixed_by_simple_edits_gets_none(name: str) -> None:
    assert suggest_name(name, PATTERNS) is None


def test_the_candidate_always_matches_one_of_the_patterns() -> None:
    for name in ("shot020_fx_v7.hip", "SHOT20 Fx V07.hip", "Prop chair.abc"):
        candidate = suggest_name(name, PATTERNS)
        if candidate is not None:
            assert any(p.match(candidate) for p in PATTERNS)


def test_a_suggestion_is_never_the_same_as_the_input() -> None:
    assert suggest_name("shot010_lighting_v003.hip", PATTERNS) != "shot010_lighting_v003.hip"


def test_no_patterns_means_no_suggestion() -> None:
    assert suggest_name("anything.hip", []) is None


def test_the_suggestion_does_not_touch_the_directory_part() -> None:
    assert suggest_name("shot010_lighting_v003.hip", PATTERNS) == "SHOT010_lighting_v003.hip"
