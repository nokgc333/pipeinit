"""cli.py の統合テスト（click.testing.CliRunner）。"""

from pathlib import Path

from click.testing import CliRunner

from pipeinit.cli import main

RULE_YAML = """
schema_version: 1
project_type: game
folder_template:
  - path: "shots"
    required: true
naming_patterns:
  - pattern: '^SHOT\\d{3}_[a-z]+_v\\d{3}\\.hip$'
    description: "shot file naming"
    applies_to: all
"""


def test_init_creates_folders_from_bundled_rule(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["init", "--type", "generic", "--path", str(tmp_path)])

    assert result.exit_code == 0
    assert "Created" in result.output


def test_init_unknown_type_exits_with_error(tmp_path: Path) -> None:
    """TC-003: 未知の--type指定時、既知の選択肢一覧をメッセージに含める。"""
    runner = CliRunner()
    result = runner.invoke(main, ["init", "--type", "foo", "--path", str(tmp_path)])

    assert result.exit_code != 0
    assert "generic" in result.output  # 既知の選択肢がヒントとして出る（Clickの標準機能）


def test_validate_reports_violation_with_custom_rules(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "bad-name.hip").touch()
    rule_path = tmp_path / "rule.yaml"
    rule_path.write_text(RULE_YAML, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(project_dir), "--rules", str(rule_path)])

    assert result.exit_code == 1
    assert "bad-name.hip" in result.output


def test_validate_no_violations_exits_zero(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "SHOT010_lighting_v003.hip").touch()
    rule_path = tmp_path / "rule.yaml"
    rule_path.write_text(RULE_YAML, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(project_dir), "--rules", str(rule_path)])

    assert result.exit_code == 0


def test_bump_dry_run_does_not_touch_filesystem(tmp_path: Path) -> None:
    """SEC-003: --apply なしではファイルシステムに変更を加えない。"""
    target = tmp_path / "SHOT010_lighting_v003.hip"
    target.touch()

    runner = CliRunner()
    result = runner.invoke(main, ["bump", str(target)])

    assert result.exit_code == 0
    assert target.exists()  # 元ファイルはそのまま
    assert "SHOT010_lighting_v004.hip" in result.output


def test_bump_apply_renames_file(tmp_path: Path) -> None:
    target = tmp_path / "SHOT010_lighting_v003.hip"
    target.touch()

    runner = CliRunner()
    result = runner.invoke(main, ["bump", str(target), "--apply"])

    assert result.exit_code == 0
    assert not target.exists()
    assert (tmp_path / "SHOT010_lighting_v004.hip").exists()
