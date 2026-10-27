"""PipeInit CLIエントリポイント（init / validate / bump / completion）。

コマンドの定義だけを置く。表示は presenter、メッセージは messages、終了コードは exit_codes。
依存の向き: cli → presenter → messages / exit_codes、cli → rules / templates / validator → fsutil。
"""

from __future__ import annotations

import os
import sys

import click
from click.shell_completion import get_completion_class

from pipeinit import commands
from pipeinit.exit_codes import (
    EXIT_NOT_WRITABLE,
    EXIT_OK,
    EXIT_PATH_TRAVERSAL,
    EXIT_RENAME_CONFLICT,
    EXIT_VIOLATIONS_OR_RULE_ERROR,
    exit_code_help,
)
from pipeinit.messages import SUPPORTED_LANGUAGES, resolve_language
from pipeinit.presenter import Printer, color_enabled

PROJECT_TYPES = ["game", "film", "generic"]
COMPLETION_SHELLS = ["bash", "zsh", "fish"]
PROGRAM_NAME = "pipeinit"
COMPLETION_VARIABLE = "_PIPEINIT_COMPLETE"

__all__ = [
    "EXIT_NOT_WRITABLE",
    "EXIT_OK",
    "EXIT_PATH_TRAVERSAL",
    "EXIT_RENAME_CONFLICT",
    "EXIT_VIOLATIONS_OR_RULE_ERROR",
    "main",
]


def _printer(ctx: click.Context) -> Printer:
    printer: Printer = ctx.obj
    return printer


@click.group(epilog=exit_code_help(resolve_language(None, os.environ)))
@click.version_option()
@click.option(
    "--quiet", "-q", is_flag=True, help="補足の出力を抑える(結果と終了コードは変わらない)。"
)
@click.option("--verbose", "-v", is_flag=True, help="詳細を標準エラーに出す。")
@click.option("--no-color", is_flag=True, help="色を付けない(環境変数 NO_COLOR でも切れる)。")
@click.option(
    "--lang",
    type=click.Choice(SUPPORTED_LANGUAGES),
    default=None,
    help="メッセージの言語(既定: 環境変数 PIPEINIT_LANG、LANG の順)。",
)
@click.pass_context
def main(ctx: click.Context, quiet: bool, verbose: bool, no_color: bool, lang: str | None) -> None:
    """PipeInit: CG/ゲームパイプライン向けフォルダ構造・命名規則自動化CLI。"""
    ctx.obj = Printer(
        lang=resolve_language(lang, os.environ),
        quiet=quiet,
        verbose=verbose,
        color=color_enabled(no_color, os.environ),
    )


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
@click.option("--json", "as_json", is_flag=True, help="結果を JSON で出す。")
@click.pass_context
def init(ctx: click.Context, project_type: str, target_path: str, as_json: bool) -> None:
    """プロジェクト種別に応じたフォルダツリーを生成する（FR-001）。"""
    sys.exit(commands.run_init(_printer(ctx), project_type, target_path, as_json))


@main.command()
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("--rules", "rules_path", default=None, type=click.Path(exists=True))
@click.option(
    "--format",
    "output_format",
    default="text",
    type=click.Choice(["text", "json"]),
)
@click.option("--json", "as_json", is_flag=True, help="--format json の短縮。")
@click.pass_context
def validate(
    ctx: click.Context,
    paths: tuple[str, ...],
    rules_path: str | None,
    output_format: str,
    as_json: bool,
) -> None:
    """命名規則違反を検出する（FR-002）。違反なし=0 / 違反あり=1。

    PATHS には、フォルダ(配下を検査)とファイル(その名前を検査。pre-commit 向け)を、複数渡せる。
    """
    sys.exit(
        commands.run_validate(_printer(ctx), paths, rules_path, as_json or output_format == "json")
    )


@main.command()
@click.argument("filename", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--apply",
    "do_apply",
    is_flag=True,
    default=False,
    help="実際にリネームを実行する（既定はドライラン、SEC-003）。",
)
@click.option("--json", "as_json", is_flag=True, help="結果を JSON で出す。")
@click.pass_context
def bump(ctx: click.Context, filename: str, do_apply: bool, as_json: bool) -> None:
    """バージョン番号を1つ繰り上げる（FR-003）。既定はドライラン。"""
    sys.exit(commands.run_bump(_printer(ctx), filename, do_apply, as_json))


@main.command()
@click.argument("shell", type=click.Choice(COMPLETION_SHELLS))
def completion(shell: str) -> None:
    """シェル補完のスクリプトを出力する。例: `eval "$(pipeinit completion bash)"`。"""
    completion_class = get_completion_class(shell)
    if completion_class is None:  # pragma: no cover - click が対応するシェルだけを選択肢にしている
        raise click.UsageError(f"unsupported shell: {shell}")
    click.echo(completion_class(main, {}, PROGRAM_NAME, COMPLETION_VARIABLE).source())


if __name__ == "__main__":
    main()
