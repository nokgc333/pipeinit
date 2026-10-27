"""設定ファイル(`.pipeinit.yaml`)の自動検出と、ユーザー設定。

優先順位: コマンドラインのオプション > プロジェクトの `.pipeinit.yaml`(カレントから親へ探す)>
ユーザー設定(`$XDG_CONFIG_HOME/pipeinit/config.yaml`、Windows は `%APPDATA%\\pipeinit\\config.yaml`)>
同梱の既定。設定できるのは `rules`(ルールファイル)・`lang`・`project_type`。
"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from pipeinit.messages import SUPPORTED_LANGUAGES

PROJECT_CONFIG_NAME = ".pipeinit.yaml"
KNOWN_KEYS = {"rules", "lang", "project_type"}


class ConfigError(Exception):
    """設定ファイルの誤り。"""


@dataclass(frozen=True)
class Settings:
    rules: str | None = None
    lang: str | None = None
    project_type: str | None = None
    source: Path | None = None


def find_project_config(start: Path) -> Path | None:
    """start から親フォルダへたどって、最初に見つかった `.pipeinit.yaml` を返す。"""
    current = start.resolve()
    for directory in (current, *current.parents):
        candidate = directory / PROJECT_CONFIG_NAME
        if candidate.is_file():
            return candidate
    return None


def user_config_path(env: Mapping[str, str], platform: str = sys.platform) -> Path | None:
    if platform == "win32":
        base = env.get("APPDATA")
        return Path(base) / "pipeinit" / "config.yaml" if base else None
    xdg = env.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "pipeinit" / "config.yaml"
    home = env.get("HOME")
    return Path(home) / ".config" / "pipeinit" / "config.yaml" if home else None


def load_config(path: Path) -> Settings:
    try:
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ConfigError(f"{path} could not be read: {exc}") from exc
    if raw is None:
        return Settings(source=path)
    if not isinstance(raw, dict):
        raise ConfigError(f"{path} must be a YAML mapping")
    unknown = set(raw) - KNOWN_KEYS
    if unknown:
        raise ConfigError(f"{path}: unknown key(s): {', '.join(sorted(map(str, unknown)))}")
    for key in KNOWN_KEYS & set(raw):
        if not isinstance(raw[key], str) or not raw[key]:
            raise ConfigError(f"{path}: {key} must be a non-empty string")
    if "lang" in raw and raw["lang"] not in SUPPORTED_LANGUAGES:
        raise ConfigError(f"{path}: lang must be one of {', '.join(SUPPORTED_LANGUAGES)}")
    rules = raw.get("rules")
    if rules is not None and not Path(rules).is_absolute():
        rules = str((path.parent / rules).resolve())
    return Settings(
        rules=rules, lang=raw.get("lang"), project_type=raw.get("project_type"), source=path
    )


def discover_settings(start: Path, env: Mapping[str, str]) -> Settings:
    """プロジェクトの設定を先に、足りない項目をユーザー設定で補う。どちらも無ければ空。"""
    project = find_project_config(start)
    user_path = user_config_path(env)
    user = load_config(user_path) if user_path is not None and user_path.is_file() else Settings()
    if project is None:
        return user
    chosen = load_config(project)
    return Settings(
        rules=chosen.rules or user.rules,
        lang=chosen.lang or user.lang,
        project_type=chosen.project_type or user.project_type,
        source=project,
    )
