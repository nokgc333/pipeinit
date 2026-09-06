"""ルールYAMLの読込・検証（SEC-001: yaml.safe_load のみ使用）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REQUIRED_KEYS = {"schema_version", "project_type", "folder_template", "naming_patterns"}


class RuleFileError(Exception):
    """ルールYAMLの読込・検証エラー（E001に対応）。"""


def load_rule_file(path: Path) -> dict[str, Any]:
    """ルールYAMLを安全に読み込み、必須キーの存在を検証する。"""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RuleFileError(f"{path} contains invalid YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise RuleFileError(f"{path} must be a YAML mapping at the top level")

    missing = REQUIRED_KEYS - raw.keys()
    if missing:
        raise RuleFileError(f"{path} is missing required key(s): {', '.join(sorted(missing))}")
    return raw
