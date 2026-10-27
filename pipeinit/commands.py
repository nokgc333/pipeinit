"""各コマンドの処理。結果の表示は presenter に任せ、終了コードを返す(sys.exit は cli.py が呼ぶ)。"""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

from pipeinit import presenter
from pipeinit.exit_codes import (
    EXIT_NOT_WRITABLE,
    EXIT_OK,
    EXIT_PATH_TRAVERSAL,
    EXIT_RENAME_CONFLICT,
    EXIT_VIOLATIONS_OR_RULE_ERROR,
)
from pipeinit.fsutil import DestinationExistsError, rename_without_overwrite
from pipeinit.houdini_env import write_houdini_env_snippet
from pipeinit.presenter import Printer
from pipeinit.rules import RuleFileError, bundled_rule_path, load_rule_file
from pipeinit.templates import PathTraversalError, generate_tree
from pipeinit.validator import NoVersionPatternError, bump_version, validate_paths


def run_init(
    printer: Printer,
    project_type: str,
    target_path: str,
    as_json: bool,
    houdini_env: bool = False,
) -> int:
    base = Path(target_path)
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        printer.error(printer.t("cannot_create", path=base, reason=exc.strerror or exc))
        return EXIT_NOT_WRITABLE

    if not os.access(base, os.W_OK):
        printer.error(printer.t("not_writable", path=base))
        return EXIT_NOT_WRITABLE

    try:
        rule = load_rule_file(bundled_rule_path(project_type))
        created, skipped = generate_tree(rule, base)
    except RuleFileError as exc:
        printer.error(str(exc))
        return EXIT_VIOLATIONS_OR_RULE_ERROR
    except PathTraversalError as exc:
        printer.error(str(exc))
        return EXIT_PATH_TRAVERSAL
    except OSError as exc:
        printer.error(printer.t("cannot_create_under", path=base, reason=exc.strerror or exc))
        return EXIT_NOT_WRITABLE

    snippet: Path | None = None
    if houdini_env:
        try:
            snippet = write_houdini_env_snippet(base)
        except OSError as exc:
            printer.error(printer.t("cannot_create_under", path=base, reason=exc.strerror or exc))
            return EXIT_NOT_WRITABLE

    if as_json:
        printer.result(presenter.init_json(created, skipped, snippet))
    else:
        presenter.show_init(printer, created, skipped)
        if snippet is not None:
            printer.info(printer.t("houdini_written", path=snippet))
    return EXIT_OK


def run_validate(
    printer: Printer, paths: Sequence[str], rules_path: str | None, as_json: bool
) -> int:
    resolved_rules = rules_path or str(bundled_rule_path("generic"))
    try:
        violations = validate_paths([Path(p) for p in paths], resolved_rules)
    except RuleFileError as exc:
        printer.error(str(exc))
        return EXIT_VIOLATIONS_OR_RULE_ERROR

    if as_json:
        printer.result(presenter.violations_json(violations))
    else:
        presenter.show_violations(printer, violations)
    return EXIT_VIOLATIONS_OR_RULE_ERROR if violations else EXIT_OK


def run_bump(printer: Printer, filename: str, do_apply: bool, as_json: bool) -> int:
    source = Path(filename)
    try:
        new_name = bump_version(source.name)
    except NoVersionPatternError as exc:
        printer.error(str(exc))
        return EXIT_VIOLATIONS_OR_RULE_ERROR

    if do_apply:
        try:
            rename_without_overwrite(source, source.parent / new_name)
        except DestinationExistsError:
            printer.error(printer.t("rename_exists", name=new_name))
            return EXIT_RENAME_CONFLICT
        except OSError as exc:
            printer.error(printer.t("cannot_rename", name=source.name, reason=exc.strerror or exc))
            return EXIT_NOT_WRITABLE

    if as_json:
        printer.result(presenter.bump_json(source.name, new_name, do_apply))
    else:
        presenter.show_bump(printer, source.name, new_name, do_apply)
    return EXIT_OK
