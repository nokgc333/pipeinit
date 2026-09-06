"""validator.py の単体テスト（TC-007〜017）。"""

from pathlib import Path

import pytest

from pipeinit.validator import (
    NoVersionPatternError,
    bump_version,
    validate_directory,
)


class TestBumpVersion:
    def test_normal_increment(self) -> None:
        """TC-013: v003 -> v004 への通常インクリメント。"""
        assert bump_version("SHOT010_lighting_v003.hip") == "SHOT010_lighting_v004.hip"

    def test_digit_overflow_expands_width(self) -> None:
        """TC-014: v999 -> v1000 への桁上げ（ゼロ埋めせず桁数拡張）。"""
        assert bump_version("SHOT010_lighting_v999.hip") == "SHOT010_lighting_v1000.hip"

    def test_no_version_part_raises(self) -> None:
        """TC-017: バージョン部を含まないファイル名はNoVersionPatternError。"""
        with pytest.raises(NoVersionPatternError, match="foo.txt"):
            bump_version("foo.txt")

    def test_last_version_marker_wins_on_multiple_matches(self) -> None:
        """バージョン部が複数マッチしうる場合は末尾を優先する。"""
        assert bump_version("v_teaser_v009.mov") == "v_teaser_v010.mov"


class TestValidateDirectory:
    def _write_rule(self, tmp_path: Path) -> Path:
        rule_path = tmp_path / "rule.yaml"
        rule_path.write_text(
            """
            schema_version: 1
            project_type: game
            folder_template: []
            naming_patterns:
              - pattern: '^SHOT\\d{3}_[a-z]+_v\\d{3}\\.hip$'
                description: "shot file naming"
                applies_to: all
            """,
            encoding="utf-8",
        )
        return rule_path

    def test_no_violations_when_all_files_match(self, tmp_path: Path) -> None:
        """TC-007: 命名規則を満たすファイルのみのディレクトリでは違反0件。"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "SHOT010_lighting_v003.hip").touch()
        rule_path = self._write_rule(tmp_path)

        violations = validate_directory(project_dir, str(rule_path))

        assert violations == []

    def test_detects_single_violation(self, tmp_path: Path) -> None:
        """TC-008: 命名規則違反ファイルを検出しファイル名と理由を含める。"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "bad-name.hip").touch()
        rule_path = self._write_rule(tmp_path)

        violations = validate_directory(project_dir, str(rule_path))

        assert len(violations) == 1
        assert violations[0]["file"] == "bad-name.hip"
        assert "shot file naming" in violations[0]["message"]

    def test_hidden_directories_are_skipped(self, tmp_path: Path) -> None:
        """TC-010: .git 等の隠しディレクトリは走査対象外。"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        git_dir = project_dir / ".git"
        git_dir.mkdir()
        (git_dir / "config").touch()
        rule_path = self._write_rule(tmp_path)

        violations = validate_directory(project_dir, str(rule_path))

        assert violations == []
