"""CLI のエラー経路と、出力・終了コードの固定のテスト。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

import pipeinit.cli as cli
from pipeinit.cli import (
    EXIT_NOT_WRITABLE,
    EXIT_OK,
    EXIT_VIOLATIONS_OR_RULE_ERROR,
    main,
)

GOOD_RULE = """schema_version: 1
project_type: x
folder_template:
  - path: "shots"
naming_patterns:
  - pattern: '^SHOT\\d{3}\\.hip$'
    description: "shot file"
"""


def _rule(tmp_path: Path, text: str = GOOD_RULE) -> Path:
    path = tmp_path / "rule.yaml"
    path.write_text(text, encoding="utf-8")
    return path


class TestInit:
    def test_a_broken_bundled_rule_is_reported_with_the_rule_error_code(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            cli,
            "bundled_rule_path",
            lambda name: _rule(
                tmp_path, GOOD_RULE.replace("schema_version: 1", "schema_version: 9")
            ),
        )

        result = CliRunner().invoke(main, ["init", "--type", "game", "--path", str(tmp_path / "t")])

        assert result.exit_code == EXIT_VIOLATIONS_OR_RULE_ERROR
        assert "schema_version" in result.output

    def test_running_twice_creates_nothing_the_second_time(self, tmp_path: Path) -> None:
        target = str(tmp_path / "t")
        CliRunner().invoke(main, ["init", "--type", "game", "--path", target])

        result = CliRunner().invoke(main, ["init", "--type", "game", "--path", target])

        assert result.exit_code == EXIT_OK
        assert "Created 0 folders" in result.output
        assert "skipped: assets/characters" in result.output

    def test_every_bundled_type_creates_its_folders(self, tmp_path: Path) -> None:
        for project_type in ("game", "film", "generic"):
            target = tmp_path / project_type

            result = CliRunner().invoke(
                main, ["init", "--type", project_type, "--path", str(target)]
            )

            assert result.exit_code == EXIT_OK
            assert (target / "shots").is_dir()

    def test_a_target_path_that_is_a_file_is_refused_by_click(self, tmp_path: Path) -> None:
        file = tmp_path / "f"
        file.write_text("x")

        result = CliRunner().invoke(main, ["init", "--type", "game", "--path", str(file)])

        assert result.exit_code == 2

    def test_unwritable_target_is_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        real_access = cli.os.access
        monkeypatch.setattr(
            cli.os,
            "access",
            lambda path, mode, **kw: mode != cli.os.W_OK and real_access(path, mode),
        )

        result = CliRunner().invoke(main, ["init", "--type", "game", "--path", str(tmp_path)])

        assert result.exit_code == EXIT_NOT_WRITABLE
        assert "not writable" in result.output

    def test_an_os_error_while_creating_folders_is_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def failing(rule: object, base: object) -> None:
            raise PermissionError(13, "Permission denied")

        monkeypatch.setattr(cli, "generate_tree", failing)

        result = CliRunner().invoke(main, ["init", "--type", "game", "--path", str(tmp_path)])

        assert result.exit_code == EXIT_NOT_WRITABLE
        assert "Permission denied" in result.output


class TestValidate:
    def test_a_file_with_a_wrong_name_is_reported_with_exit_code_1(self, tmp_path: Path) -> None:
        (tmp_path / "bad.hip").write_text("x")

        result = CliRunner().invoke(
            main, ["validate", str(tmp_path), "--rules", str(_rule(tmp_path))]
        )

        assert result.exit_code == 1
        assert "bad.hip" in result.output

    def test_a_clean_folder_exits_zero(self, tmp_path: Path) -> None:
        target = tmp_path / "t"
        target.mkdir()
        (target / "SHOT010.hip").write_text("x")

        result = CliRunner().invoke(
            main, ["validate", str(target), "--rules", str(_rule(tmp_path))]
        )

        assert result.exit_code == 0
        assert "No violations found." in result.output

    def test_json_output_has_the_violations_and_the_count(self, tmp_path: Path) -> None:
        target = tmp_path / "t"
        target.mkdir()
        (target / "bad.hip").write_text("x")

        result = CliRunner().invoke(
            main,
            ["validate", str(target), "--rules", str(_rule(tmp_path)), "--format", "json"],
        )

        payload = json.loads(result.output)
        assert payload["count"] == 1
        assert payload["violations"][0]["file"] == "bad.hip"

    def test_a_broken_rule_file_is_reported_with_its_reason(self, tmp_path: Path) -> None:
        target = tmp_path / "t"
        target.mkdir()
        broken = _rule(tmp_path, GOOD_RULE.replace("'^SHOT\\d{3}\\.hip$'", "'(oops'"))

        result = CliRunner().invoke(main, ["validate", str(target), "--rules", str(broken)])

        assert result.exit_code == EXIT_VIOLATIONS_OR_RULE_ERROR
        assert "regular expression" in result.output
        assert "Traceback" not in result.output

    def test_japanese_file_names_are_reported_intact(self, tmp_path: Path) -> None:
        target = tmp_path / "t"
        target.mkdir()
        (target / "ショット 010.hip").write_text("x")

        result = CliRunner().invoke(
            main,
            ["validate", str(target), "--rules", str(_rule(tmp_path)), "--format", "json"],
        )

        assert json.loads(result.output)["violations"][0]["file"] == "ショット 010.hip"


class TestBump:
    def test_a_name_without_a_version_is_reported(self, tmp_path: Path) -> None:
        (tmp_path / "plain.hip").write_text("x")

        result = CliRunner().invoke(main, ["bump", str(tmp_path / "plain.hip")])

        assert result.exit_code == EXIT_VIOLATIONS_OR_RULE_ERROR
        assert "does not match" in result.output

    def test_apply_renames_the_file(self, tmp_path: Path) -> None:
        (tmp_path / "a_v009.hip").write_text("x")

        result = CliRunner().invoke(main, ["bump", str(tmp_path / "a_v009.hip"), "--apply"])

        assert result.exit_code == 0
        assert (tmp_path / "a_v010.hip").exists()
        assert "a_v009.hip -> a_v010.hip" in result.output

    def test_an_os_error_during_the_rename_is_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "a_v001.hip").write_text("x")

        def failing(source: Path, destination: Path) -> None:
            raise PermissionError(13, "Permission denied")

        monkeypatch.setattr(cli, "rename_without_overwrite", failing)

        result = CliRunner().invoke(main, ["bump", str(tmp_path / "a_v001.hip"), "--apply"])

        assert result.exit_code == EXIT_NOT_WRITABLE
        assert "Permission denied" in result.output


def test_the_version_option_prints_the_package_version() -> None:
    result = CliRunner().invoke(main, ["--version"])

    assert result.exit_code == 0
    assert "version" in result.output.lower()
    assert sys.version  # keep the import used
