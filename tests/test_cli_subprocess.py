"""インストールしたコマンドを、実際のプロセスとして動かす結合テスト(標準出力・標準エラー・終了コードを固定する)。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

RULE = """schema_version: 1
project_type: x
folder_template:
  - path: "shots"
naming_patterns:
  - pattern: '^SHOT\\d{3}\\.hip$'
    description: "shot file"
"""


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pipeinit.cli", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        check=False,
    )


def test_help_lists_the_three_commands() -> None:
    result = run("--help")

    assert result.returncode == 0
    for command in ("init", "validate", "bump"):
        assert command in result.stdout


def test_init_prints_what_it_created_and_exits_zero(tmp_path: Path) -> None:
    result = run("init", "--type", "generic", "--path", str(tmp_path / "p"))

    assert result.returncode == 0
    assert result.stdout.startswith("Created 3 folders, skipped 0")
    assert "  created: assets" in result.stdout
    assert result.stderr == ""
    assert (tmp_path / "p" / "assets").is_dir()


def test_init_with_an_unknown_type_exits_2_with_a_usage_message(tmp_path: Path) -> None:
    result = run("init", "--type", "nope", "--path", str(tmp_path))

    assert result.returncode == 2
    assert "Invalid value for '--type'" in result.stderr


def test_validate_exits_1_and_names_the_file_on_stdout(tmp_path: Path) -> None:
    (tmp_path / "t").mkdir()
    (tmp_path / "t" / "bad.hip").write_text("x")
    rule = tmp_path / "rule.yaml"
    rule.write_text(RULE, encoding="utf-8")

    result = run("validate", str(tmp_path / "t"), "--rules", str(rule))

    assert result.returncode == 1
    assert result.stdout.startswith("bad.hip: 'bad.hip' does not match:")
    assert result.stderr == ""


def test_validate_json_is_machine_readable(tmp_path: Path) -> None:
    (tmp_path / "t").mkdir()
    (tmp_path / "t" / "SHOT010.hip").write_text("x")
    rule = tmp_path / "rule.yaml"
    rule.write_text(RULE, encoding="utf-8")

    result = run("validate", str(tmp_path / "t"), "--rules", str(rule), "--format", "json")

    assert result.returncode == 0
    assert json.loads(result.stdout) == {"violations": [], "count": 0}


def test_a_broken_rule_file_goes_to_stderr_with_exit_1(tmp_path: Path) -> None:
    (tmp_path / "t").mkdir()
    rule = tmp_path / "rule.yaml"
    rule.write_text("schema_version: 5\n", encoding="utf-8")

    result = run("validate", str(tmp_path / "t"), "--rules", str(rule))

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.startswith("Error:")
    assert "Traceback" not in result.stderr


def test_bump_is_a_dry_run_unless_apply_is_given(tmp_path: Path) -> None:
    (tmp_path / "a_v001.hip").write_text("x")

    dry = run("bump", str(tmp_path / "a_v001.hip"))
    applied = run("bump", str(tmp_path / "a_v001.hip"), "--apply")

    assert dry.stdout.strip() == "a_v001.hip -> a_v002.hip (dry-run, use --apply to rename)"
    assert applied.stdout.strip() == "a_v001.hip -> a_v002.hip"
    assert (tmp_path / "a_v002.hip").exists()


def test_bump_conflict_exits_7_and_keeps_the_existing_file(tmp_path: Path) -> None:
    (tmp_path / "a_v001.hip").write_text("old")
    (tmp_path / "a_v002.hip").write_text("keep")

    result = run("bump", str(tmp_path / "a_v001.hip"), "--apply")

    assert result.returncode == 7
    assert "file already exists" in result.stderr
    assert (tmp_path / "a_v002.hip").read_text() == "keep"
