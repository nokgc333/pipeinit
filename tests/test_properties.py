"""Hypothesis による性質テスト(バージョンの繰り上げ・命名検証・パスの安全性)。"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from pipeinit.templates import PathTraversalError, resolve_safe_path
from pipeinit.validator import (
    VERSION_RE,
    NoVersionPatternError,
    bump_version,
    validate_directory,
)

stems = st.text(
    alphabet=st.characters(blacklist_categories=("Cs", "Cc"), blacklist_characters="/\\\x00"),
    min_size=1,
    max_size=20,
)
extensions = st.from_regex(r"\.[A-Za-z0-9]{1,5}", fullmatch=True)
numbers = st.integers(min_value=0, max_value=10**6)
widths = st.integers(min_value=1, max_value=7)


def _name(stem: str, number: int, width: int, ext: str) -> str:
    return f"{stem}_v{str(number).zfill(width)}{ext}"


@given(stems, numbers, widths, extensions)
def test_bumping_always_gives_the_next_number(stem: str, number: int, width: int, ext: str) -> None:
    name = _name(stem, number, width, ext)

    match = VERSION_RE.match(bump_version(name))

    assert match is not None
    before = VERSION_RE.match(name)
    assert before is not None
    assert int(match.group("num")) == int(before.group("num")) + 1


@given(stems, numbers, widths, extensions)
def test_bumping_keeps_the_stem_and_the_extension(
    stem: str, number: int, width: int, ext: str
) -> None:
    name = _name(stem, number, width, ext)
    before = VERSION_RE.match(name)
    after = VERSION_RE.match(bump_version(name))

    assert before is not None and after is not None
    assert (after.group("stem"), after.group("ext")) == (before.group("stem"), before.group("ext"))


@given(stems, numbers, widths, extensions)
def test_the_zero_padding_width_never_shrinks(stem: str, number: int, width: int, ext: str) -> None:
    name = _name(stem, number, width, ext)
    before = VERSION_RE.match(name)
    after = VERSION_RE.match(bump_version(name))

    assert before is not None and after is not None
    assert len(after.group("num")) >= len(before.group("num"))


@given(stems, widths, extensions)
def test_a_carry_widens_the_number_instead_of_wrapping(stem: str, width: int, ext: str) -> None:
    top = "9" * width
    name = f"{stem}_v{top}{ext}"

    assert bump_version(name) == f"{stem}_v1{'0' * width}{ext}"


@given(st.text(max_size=30))
def test_a_name_is_either_bumped_or_refused_never_a_crash(name: str) -> None:
    try:
        result = bump_version(name)
    except NoVersionPatternError:
        assert VERSION_RE.match(name) is None
    else:
        assert VERSION_RE.match(result) is not None


@given(stems, numbers, widths, extensions)
def test_bumping_twice_adds_two(stem: str, number: int, width: int, ext: str) -> None:
    name = _name(stem, number, width, ext)
    twice = VERSION_RE.match(bump_version(bump_version(name)))
    once = VERSION_RE.match(name)

    assert twice is not None and once is not None
    assert int(twice.group("num")) == int(once.group("num")) + 2


@given(st.lists(st.sampled_from(["a", "b", "..", ".", "c d", "日本"]), min_size=1, max_size=6))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_a_resolved_path_is_always_inside_the_base_or_refused(parts: list[str]) -> None:
    base = Path("/tmp/pipeinit-base")
    relative = "/".join(parts)

    try:
        resolved = resolve_safe_path(base, relative)
    except PathTraversalError:
        return

    assert resolved.is_relative_to(base.resolve())


@settings(max_examples=40, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    st.lists(st.text(alphabet="abcXYZ012_-. ", min_size=1, max_size=12), max_size=8, unique=True)
)
def test_validation_reports_exactly_the_files_that_do_not_match(
    tmp_path_factory: pytest.TempPathFactory, names: list[str]
) -> None:
    names = [
        n
        for n in names
        if not n.startswith(".") and n.strip() == n and "/" not in n and not n.endswith(".")
    ]
    assume(len({n.lower() for n in names}) == len(names))
    folder = tmp_path_factory.mktemp("scan")
    rule = folder / "rule.yaml"
    rule.write_text(
        "schema_version: 1\nproject_type: x\nfolder_template: []\n"
        "naming_patterns:\n  - pattern: '^[A-Z]+\\d+$'\n    description: \"upper then digits\"\n",
        encoding="utf-8",
    )
    target = folder / "t"
    target.mkdir()
    for name in names:
        (target / name).write_text("x")

    reported = {v["file"] for v in validate_directory(target, str(rule))}

    expected = {n for n in names if not re.match(r"^[A-Z]+\d+$", n)}
    assert reported == expected
