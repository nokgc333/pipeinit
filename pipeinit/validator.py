"""命名規則バリデーション（FR-002）とバージョン番号計算（FR-003）。"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from pathlib import Path

from pipeinit.fsutil import iter_files
from pipeinit.rules import load_rule_file

VERSION_RE = re.compile(r"^(?P<stem>.+_v)(?P<num>\d+)(?P<ext>\.\w+)$")


class NoVersionPatternError(Exception):
    """ファイル名がバージョンパターンに一致しない場合に送出（E004）。"""


def bump_version(filename: str) -> str:
    """ファイル名末尾のバージョン番号を1つ繰り上げる。

    v999 -> v1000 のような桁上げは、ゼロ埋めせず桁数を拡張する。
    """
    match = VERSION_RE.match(filename)
    if match is None:
        raise NoVersionPatternError(f"'{filename}' does not match any known version pattern")

    stem, num_str, ext = match.group("stem", "num", "ext")
    width = len(num_str)
    next_num = int(num_str) + 1
    next_str = str(next_num)
    if len(next_str) < width:
        next_str = next_str.zfill(width)
    return f"{stem}{next_str}{ext}"


def _compile_patterns(rules_path: str) -> list[tuple[re.Pattern[str], str]]:
    rule = load_rule_file(Path(rules_path))
    return [
        (re.compile(entry["pattern"]), entry["description"])
        for entry in rule.get("naming_patterns", [])
    ]


def _violation(
    relative: str, filename: str, patterns: list[tuple[re.Pattern[str], str]]
) -> dict[str, str]:
    reasons = "; ".join(description for _, description in patterns)
    return {
        "file": relative,
        "rule": reasons,
        "message": f"'{filename}' does not match: {reasons}",
    }


def validate_directory(
    target: Path, rules_path: str, on_file: Callable[[int], None] | None = None
) -> list[dict[str, str]]:
    """target 配下のファイル名を naming_patterns と照合し、違反一覧を返す。

    .git 等の隠しディレクトリは走査対象から除外する（TC-010）。
    `on_file` には、走査したファイルの数(1 から)を、1 件ごとに渡す(進捗の表示用)。
    """
    patterns = _compile_patterns(rules_path)
    violations: list[dict[str, str]] = []
    for count, path in enumerate(iter_files(target), start=1):
        if on_file is not None:
            on_file(count)
        if not _matches_any(path.name, patterns):
            violations.append(_violation(str(path.relative_to(target)), path.name, patterns))
    return violations


def validate_paths(paths: Sequence[Path], rules_path: str) -> list[dict[str, str]]:
    """ファイルとフォルダの混在した一覧を検査する(pre-commit は、ファイルを渡す)。

    ファイルは、そのファイル名を検査する。フォルダは、配下のファイルを検査する。
    """
    patterns = _compile_patterns(rules_path)
    violations: list[dict[str, str]] = []
    for target in paths:
        if target.is_dir():
            violations.extend(validate_directory(target, rules_path))
        elif not _matches_any(target.name, patterns):
            violations.append(_violation(str(target), target.name, patterns))
    return violations


def _matches_any(filename: str, patterns: list[tuple[re.Pattern[str], str]]) -> bool:
    return any(pattern.match(filename) for pattern, _ in patterns)
