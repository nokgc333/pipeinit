"""違反したファイル名への、リネーム候補。

よくある間違い(区切り・大文字小文字・ゼロ埋め・拡張子の大文字)を直す、決まった小さな変換だけを、
組み合わせて試し、ルールのパターンに合った最初の候補を返す。見つからなければ None。
候補を出すだけで、ファイルは変更しない(ADR-0003)。
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Callable, Sequence

SEPARATORS = re.compile(r"[ \-]+")
VERSION = re.compile(r"(?i)(_v)(\d+)(?=\.|$)")
SHOT_NUMBER = re.compile(r"(?i)^(shot)(\d{1,3})(?=_)")


def _separators(name: str) -> str:
    stem, dot, ext = name.rpartition(".")
    if not dot:
        return SEPARATORS.sub("_", name)
    return SEPARATORS.sub("_", stem) + "." + ext


def _extension_lower(name: str) -> str:
    stem, dot, ext = name.rpartition(".")
    return f"{stem}.{ext.lower()}" if dot else name


def _version_padding(name: str) -> str:
    return VERSION.sub(lambda m: f"_v{int(m.group(2)):03d}", name)


def _shot_prefix(name: str) -> str:
    return SHOT_NUMBER.sub(lambda m: f"SHOT{int(m.group(2)):03d}", name)


def _lower_middle(name: str) -> str:
    parts = name.split("_")
    if len(parts) >= 3:
        parts = [
            parts[0],
            *[p.lower() if not VERSION.fullmatch("_" + p) else p for p in parts[1:-1]],
            parts[-1],
        ]
    return "_".join(parts)


def _capitalize_first(name: str) -> str:
    return name[:1].upper() + name[1:]


TRANSFORMS: tuple[Callable[[str], str], ...] = (
    _separators,
    _extension_lower,
    _version_padding,
    _shot_prefix,
    _lower_middle,
    _capitalize_first,
)


def suggest_name(name: str, patterns: Sequence[re.Pattern[str]]) -> str | None:
    """name を、いずれかのパターンに合わせる候補を返す。すでに合っているとき・直せないときは None。"""
    if not patterns or any(p.match(name) for p in patterns):
        return None
    for size in range(1, len(TRANSFORMS) + 1):
        for combination in itertools.combinations(TRANSFORMS, size):
            candidate = name
            for transform in combination:
                candidate = transform(candidate)
            if candidate != name and any(p.match(candidate) for p in patterns):
                return candidate
    return None
