"""ルールYAMLの読込・検証（SEC-001: yaml.safe_load のみ使用）。

不正な値は、どのファイルのどの項目か(`naming_patterns[0].pattern` のように)が分かる
`RuleFileError` にする(トレースバックを出さない)。
"""

from __future__ import annotations

import re
from pathlib import Path, PureWindowsPath
from typing import Any

import yaml

SUPPORTED_SCHEMA_VERSION = 1
REQUIRED_KEYS = {"schema_version", "project_type", "folder_template", "naming_patterns"}
DATA_DIR = Path(__file__).parent / "data"


class RuleFileError(Exception):
    """ルールYAMLの読込・検証エラー（E001に対応）。"""


def bundled_rule_path(project_type: str) -> Path:
    """パッケージに同梱した、プロジェクト種別のルールのパス。"""
    return DATA_DIR / f"{project_type}.yaml"


def _read_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RuleFileError(f"{path} contains invalid YAML: {exc}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise RuleFileError(f"{path} could not be read: {exc}") from exc


def _is_absolute(value: str) -> bool:
    return (
        value.startswith(("/", "\\", "~"))
        or Path(value).is_absolute()
        or PureWindowsPath(value).is_absolute()
    )


def _check_folder_template(path: Path, entries: Any) -> None:
    if not isinstance(entries, list):
        raise RuleFileError(f"{path}: folder_template must be a list")
    for index, entry in enumerate(entries):
        where = f"{path}: folder_template[{index}]"
        if not isinstance(entry, dict):
            raise RuleFileError(f"{where} must be a mapping with a 'path'")
        value = entry.get("path")
        if not isinstance(value, str) or not value.strip():
            raise RuleFileError(f"{where}.path must be a non-empty string")
        if "\x00" in value:
            raise RuleFileError(f"{where}.path must not contain a null byte")
        if _is_absolute(value):
            raise RuleFileError(f"{where}.path must be relative to the target directory")


def _check_naming_patterns(path: Path, entries: Any) -> None:
    if not isinstance(entries, list):
        raise RuleFileError(f"{path}: naming_patterns must be a list")
    for index, entry in enumerate(entries):
        where = f"{path}: naming_patterns[{index}]"
        if not isinstance(entry, dict):
            raise RuleFileError(f"{where} must be a mapping with a 'pattern' and a 'description'")
        pattern = entry.get("pattern")
        if not isinstance(pattern, str) or not pattern:
            raise RuleFileError(f"{where}.pattern must be a non-empty string")
        try:
            re.compile(pattern)
        except re.error as exc:
            raise RuleFileError(
                f"{where}.pattern is not a valid regular expression: {exc}"
            ) from exc
        description = entry.get("description")
        if not isinstance(description, str) or not description.strip():
            raise RuleFileError(f"{where}.description must be a non-empty string")


def load_rule_file(path: Path) -> dict[str, Any]:
    """ルールYAMLを安全に読み込み、構造と値を検証する。"""
    raw = _read_yaml(path)

    if not isinstance(raw, dict):
        raise RuleFileError(f"{path} must be a YAML mapping at the top level")

    missing = REQUIRED_KEYS - raw.keys()
    if missing:
        raise RuleFileError(f"{path} is missing required key(s): {', '.join(sorted(missing))}")

    version = raw["schema_version"]
    if isinstance(version, bool) or version != SUPPORTED_SCHEMA_VERSION:
        raise RuleFileError(
            f"{path}: schema_version must be {SUPPORTED_SCHEMA_VERSION}, got {version!r}"
        )
    if not isinstance(raw["project_type"], str) or not raw["project_type"]:
        raise RuleFileError(f"{path}: project_type must be a non-empty string")
    _check_folder_template(path, raw["folder_template"])
    _check_naming_patterns(path, raw["naming_patterns"])
    return raw
