"""フォルダツリー生成（SEC-002: パストラバーサル検証を含む）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class PathTraversalError(Exception):
    """生成先パスがベースディレクトリの外側を指している場合に送出（E006）。"""


def resolve_safe_path(base: Path, relative: str) -> Path:
    """relative を base 配下に正規化する。base の外側を指す場合は例外を送出する。"""
    base_resolved = base.resolve()
    resolved = (base_resolved / relative).resolve()
    if not resolved.is_relative_to(base_resolved):
        raise PathTraversalError(f"folder_template path '{relative}' escapes the target directory")
    return resolved


def generate_tree(rule: dict[str, Any], base: Path) -> tuple[list[str], list[str]]:
    """rule['folder_template'] に従って base 配下にフォルダを生成する。

    既存のフォルダは変更せずスキップする（冪等性）。
    戻り値は (created の相対パス一覧, skipped の相対パス一覧)。
    パストラバーサルを検出した場合は何も作成せず PathTraversalError を送出する。
    """
    entries = rule.get("folder_template", [])

    # 先に全パスを検証してから生成する（一部だけ作成された中途半端な状態を避ける）
    resolved_entries = [
        (entry["path"], resolve_safe_path(base, entry["path"])) for entry in entries
    ]

    created: list[str] = []
    skipped: list[str] = []
    for relative_path, absolute_path in resolved_entries:
        if absolute_path.is_dir():
            skipped.append(relative_path)
            continue
        absolute_path.mkdir(parents=True, exist_ok=False)
        created.append(relative_path)

    return created, skipped
