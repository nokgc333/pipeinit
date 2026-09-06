"""PipeInit CLIエントリポイント（init / validate / bump）。"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click

from pipeinit.rules import RuleFileError, load_rule_file
from pipeinit.templates import PathTraversalError, generate_tree
from pipeinit.validator import NoVersionPatternError, bump_version, validate_directory

BUNDLED_RULES_DIR = Path(__file__).parent.parent / "rules"
PROJECT_TYPES = ["game", "film", "generic"]

# exit code規約（仕様書_v2.md §5.4）
EXIT_OK = 0
EXIT_VIOLATIONS_OR_RULE_ERROR = 1
EXIT_UNKNOWN_TYPE = 3
EXIT_PATH_NOT_FOUND = 4
EXIT_NOT_WRITABLE = 5
EXIT_PATH_TRAVERSAL = 6
EXIT_RENAME_CONFLICT = 7


@click.group()
@click.version_option()
def main() -> None:
    """PipeInit: CG/ゲームパイプライン向けフォルダ構造・命名規則自動化CLI。"""


@main.command()
@click.option(
    "--type",
    "project_type",
    required=True,
    type=click.Choice(PROJECT_TYPES),
    help="プロジェクト種別。",
)
@click.option(
    "--path",
    "target_path",
    default=".",
    type=click.Path(file_okay=False),
    help="生成先ディレクトリ（既定: カレントディレクトリ）。",
)
def init(project_type: str, target_path: str) -> None:
    """プロジェクト種別に応じたフォルダツリーを生成する（FR-001）。"""
    base = Path(target_path)
    base.mkdir(parents=True, exist_ok=True)

    if not os.access(base, os.W_OK):
        click.echo(f"Error: '{base}' is not writable", err=True)
        sys.exit(EXIT_NOT_WRITABLE)

    try:
        rule = load_rule_file(BUNDLED_RULES_DIR / f"{project_type}.yaml")
        created, skipped = generate_tree(rule, base)
    except RuleFileError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(EXIT_VIOLATIONS_OR_RULE_ERROR)
    except PathTraversalError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(EXIT_PATH_TRAVERSAL)

    click.echo(f"Created {len(created)} folders, skipped {len(skipped)} (already exist)")
    for path in created:
        click.echo(f"  created: {path}")
    for path in skipped:
        click.echo(f"  skipped: {path}")


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False))
@click.option("--rules", "rules_path", default=None, type=click.Path(exists=True))
@click.option(
    "--format",
    "output_format",
    default="text",
    type=click.Choice(["text", "json"]),
)
def validate(path: str, rules_path: str | None, output_format: str) -> None:
    """命名規則違反を検出する（FR-002）。違反なし=0 / 違反あり=1。"""
    resolved_rules = rules_path or str(BUNDLED_RULES_DIR / "generic.yaml")

    try:
        violations = validate_directory(Path(path), resolved_rules)
    except RuleFileError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(EXIT_VIOLATIONS_OR_RULE_ERROR)

    if output_format == "json":
        click.echo(
            json.dumps({"violations": violations, "count": len(violations)}, ensure_ascii=False)
        )
    elif violations:
        for v in violations:
            click.echo(f"{v['file']}: {v['message']}")
    else:
        click.echo("No violations found.")

    sys.exit(EXIT_VIOLATIONS_OR_RULE_ERROR if violations else EXIT_OK)


@main.command()
@click.argument("filename", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--apply",
    "do_apply",
    is_flag=True,
    default=False,
    help="実際にリネームを実行する（既定はドライラン、SEC-003）。",
)
def bump(filename: str, do_apply: bool) -> None:
    """バージョン番号を1つ繰り上げる（FR-003）。既定はドライラン。"""
    source = Path(filename)

    try:
        new_name = bump_version(source.name)
    except NoVersionPatternError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(EXIT_VIOLATIONS_OR_RULE_ERROR)

    destination = source.parent / new_name

    if not do_apply:
        click.echo(f"{source.name} -> {new_name} (dry-run, use --apply to rename)")
        sys.exit(EXIT_OK)

    if destination.exists():
        click.echo(f"Error: cannot rename to '{new_name}': file already exists", err=True)
        sys.exit(EXIT_RENAME_CONFLICT)

    source.rename(destination)
    click.echo(f"{source.name} -> {new_name}")
