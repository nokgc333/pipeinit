"""命名規則バリデーション（FR-002）とバージョン番号計算（FR-003）。"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

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


def validate_directory(target: Path, rules_path: str) -> list[dict[str, str]]:
    """target 配下のファイル名を naming_patterns と照合し、違反一覧を返す。

    .git 等の隠しディレクトリは走査対象から除外する（TC-010）。
    """
    rule = load_rule_file(Path(rules_path))
    patterns = [
        (re.compile(entry["pattern"]), entry["description"])
        for entry in rule.get("naming_patterns", [])
    ]

    violations: list[dict[str, str]] = []
    for path in _iter_files(target):
        filename = path.name
        if not _matches_any(filename, patterns):
            relative = str(path.relative_to(target))
            reasons = "; ".join(description for _, description in patterns)
            violations.append(
                {
                    "file": relative,
                    "rule": reasons,
                    "message": f"'{filename}' does not match: {reasons}",
                }
            )
    return violations


def _iter_files(target: Path) -> Iterator[Path]:
    for path in sorted(target.rglob("*")):
        if path.is_dir():
            continue
        if any(part.startswith(".") for part in path.relative_to(target).parts):
            continue
        yield path


def _matches_any(filename: str, patterns: list[tuple[re.Pattern[str], str]]) -> bool:
    return any(pattern.match(filename) for pattern, _ in patterns)
