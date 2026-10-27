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


def test_every_adr_is_listed_in_the_readme_and_the_docs_index() -> None:
    adrs = sorted((ROOT / "docs" / "adr").glob("*.md"))
    readme = _read("README.md")

    assert len(adrs) >= 6
    for adr in adrs:
        assert f"docs/adr/{adr.name}" in readme, adr.name


def test_the_readme_has_an_english_summary_an_image_a_diagram_and_the_exit_code_table() -> None:
    readme = _read("README.md")

    assert "English summary" in readme
    assert (ROOT / "docs/images/demo.png").is_file()
    assert "docs/images/demo.png" in readme
    assert "```mermaid" in readme
    for code in ("| 0 |", "| 1 |", "| 2 |", "| 5 |", "| 6 |", "| 7 |"):
        assert code in readme


def test_the_readme_exit_codes_match_the_code() -> None:
    from pipeinit.exit_codes import EXIT_CODE_TABLE

    readme = _read("README.md")

    for code, *_ in EXIT_CODE_TABLE:
        assert f"| {code} |" in readme


def test_the_old_version_of_the_specs_is_archived_and_the_current_one_is_linked() -> None:
    assert (ROOT / "docs/archive/要件定義書_v1.md").is_file()
    assert not (ROOT / "docs/要件定義書.md").exists()
    assert "要件定義書_v2.md" in _read("docs/README.md")


def test_contributing_and_the_docs_index_exist() -> None:
    assert "Conventional Commits" in _read("CONTRIBUTING.md")
    assert (ROOT / "docs/README.md").is_file()


def test_every_relative_link_in_the_readme_points_to_a_file() -> None:
    import re

    for link in re.findall(
        r"\]\(((?:docs|CHANGELOG|CONTRIBUTING|LICENSE)[^)#]*)\)", _read("README.md")
    ):
        assert (ROOT / link).exists(), link
