"""配布に関わる設定のテスト(同梱のデータ・コマンド・メタデータ・CI)。"""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
PROJECT = PYPROJECT["project"]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_the_rules_are_shipped_inside_the_package() -> None:
    package_data = PYPROJECT["tool"]["setuptools"]["package-data"]["pipeinit"]

    assert "data/*.yaml" in package_data
    assert (ROOT / "pipeinit" / "data" / "generic.yaml").is_file()
    assert not (ROOT / "rules").exists()


def test_the_typed_marker_is_shipped() -> None:
    assert (ROOT / "pipeinit" / "py.typed").is_file()
    assert "py.typed" in PYPROJECT["tool"]["setuptools"]["package-data"]["pipeinit"]


def test_the_command_is_exposed() -> None:
    assert PROJECT["scripts"]["pipeinit"] == "pipeinit.cli:run"


def test_the_version_matches_the_latest_changelog_entry() -> None:
    assert f"## [{PROJECT['version']}]" in _read("CHANGELOG.md")


def test_the_metadata_a_package_index_shows_is_filled_in() -> None:
    assert PROJECT["license"] == "MIT"
    assert PROJECT["classifiers"] and PROJECT["keywords"]
    assert {"Homepage", "Repository", "Changelog"} <= set(PROJECT["urls"])
    assert "Houdini" in PROJECT["description"]


def test_ci_runs_on_three_operating_systems_and_three_pythons() -> None:
    ci = _read(".github/workflows/ci.yml")

    for name in ("ubuntu-latest", "macos-latest", "windows-latest", '"3.11"', '"3.12"', '"3.13"'):
        assert name in ci
    assert "twine check" in ci
    assert "cov-fail-under=95" in ci


def test_the_release_workflow_publishes_without_a_stored_token() -> None:
    release = _read(".github/workflows/release.yml")

    assert "id-token: write" in release
    assert "password" not in release


def test_updates_are_automated_and_the_lock_and_hooks_exist() -> None:
    assert "package-ecosystem: pip" in _read(".github/dependabot.yml")
    assert (ROOT / "uv.lock").is_file()
    assert "gitleaks" in _read(".pre-commit-config.yaml")
    assert "pipeinit-validate" in _read(".pre-commit-hooks.yaml")
