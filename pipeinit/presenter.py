"""出力の整形(メッセージ・色・--quiet / --verbose・JSON)。コマンドの定義(cli.py)からは、表示の詳細を切り離す。"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click

from pipeinit.messages import translate


@dataclass(frozen=True)
class Printer:
    lang: str = "en"
    quiet: bool = False
    verbose: bool = False
    color: bool = True

    def t(self, key: str, **params: object) -> str:
        return translate(key, self.lang, **params)

    def _style(self, text: str, fg: str, bold: bool = False) -> str:
        return click.style(text, fg=fg, bold=bold) if self.color else text

    def result(self, text: str) -> None:
        """コマンドの主な結果。`--quiet` でも出す(終了コードと合わせて使うため)。"""
        click.echo(text)

    def info(self, text: str) -> None:
        """補足。`--quiet` では出さない。"""
        if not self.quiet:
            click.echo(text)

    def detail(self, text: str) -> None:
        """詳細。`--verbose` のときだけ、標準エラーに出す(標準出力の形式を壊さない)。"""
        if self.verbose and not self.quiet:
            click.echo(text, err=True)

    def error(self, message: str) -> None:
        prefix = self._style(self.t("error_prefix"), "red", bold=True)
        click.echo(f"{prefix}: {message}", err=True)


def color_enabled(no_color_option: bool, env: Mapping[str, str]) -> bool:
    """`--no-color` と、環境変数 `NO_COLOR`(https://no-color.org)で、色を切る。"""
    return not (no_color_option or env.get("NO_COLOR"))


def show_init(printer: Printer, created: Sequence[str], skipped: Sequence[str]) -> None:
    printer.info(printer.t("created_summary", created=len(created), skipped=len(skipped)))
    for path in created:
        printer.info(printer.t("created_item", path=path))
    for path in skipped:
        printer.info(printer.t("skipped_item", path=path))


def init_json(
    created: Sequence[str], skipped: Sequence[str], houdini_env: Path | None = None
) -> str:
    payload: dict[str, Any] = {"created": list(created), "skipped": list(skipped)}
    if houdini_env is not None:
        payload["houdini_env"] = str(houdini_env)
    return json.dumps(payload, ensure_ascii=False)


def show_violations(printer: Printer, violations: Sequence[Mapping[str, str]]) -> None:
    if not violations:
        printer.info(printer.t("no_violations"))
        return
    for violation in violations:
        name = os.path.basename(violation["file"])
        file = printer._style(violation["file"], "yellow")
        printer.result(printer.t("violation", file=file, name=name, rule=violation["rule"]))
        if violation.get("suggestion"):
            printer.result(printer.t("suggestion", name=violation["suggestion"]))


def violations_json(violations: Sequence[Mapping[str, Any]]) -> str:
    return json.dumps(
        {"violations": list(violations), "count": len(violations)}, ensure_ascii=False
    )


def show_bump(printer: Printer, old: str, new: str, applied: bool) -> None:
    key = "bump_done" if applied else "bump_dry_run"
    printer.result(printer.t(key, old=old, new=new))


def bump_json(old: str, new: str, applied: bool) -> str:
    return json.dumps({"old": old, "new": new, "applied": applied}, ensure_ascii=False)
