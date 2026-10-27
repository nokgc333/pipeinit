"""メッセージの日本語・英語の切り替え(`--lang` > `PIPEINIT_LANG` > `LANG`)。"""

from __future__ import annotations

from collections.abc import Mapping

SUPPORTED_LANGUAGES = ("ja", "en")

CATALOG: dict[str, dict[str, str]] = {
    "created_summary": {
        "en": "Created {created} folders, skipped {skipped} (already exist)",
        "ja": "{created} 個のフォルダを作成、{skipped} 個は既存のためスキップ",
    },
    "created_item": {"en": "  created: {path}", "ja": "  作成: {path}"},
    "skipped_item": {"en": "  skipped: {path}", "ja": "  スキップ: {path}"},
    "no_violations": {"en": "No violations found.", "ja": "違反はありません。"},
    "violation": {
        "en": "{file}: '{name}' does not match: {rule}",
        "ja": "{file}: '{name}' は次の規則に合いません: {rule}",
    },
    "suggestion": {"en": "  suggestion: {name}", "ja": "  リネーム候補: {name}"},
    "bump_dry_run": {
        "en": "{old} -> {new} (dry-run, use --apply to rename)",
        "ja": "{old} -> {new} (ドライラン。実行するには --apply)",
    },
    "bump_done": {"en": "{old} -> {new}", "ja": "{old} -> {new}"},
    "error_prefix": {"en": "Error", "ja": "エラー"},
    "not_writable": {
        "en": "'{path}' is not writable",
        "ja": "'{path}' に書き込めません",
    },
    "cannot_create": {
        "en": "cannot create '{path}': {reason}",
        "ja": "'{path}' を作成できません: {reason}",
    },
    "cannot_create_under": {
        "en": "cannot create folders under '{path}': {reason}",
        "ja": "'{path}' の下にフォルダを作成できません: {reason}",
    },
    "cannot_rename": {
        "en": "cannot rename '{name}': {reason}",
        "ja": "'{name}' をリネームできません: {reason}",
    },
    "rename_exists": {
        "en": "cannot rename to '{name}': file already exists",
        "ja": "'{name}' にリネームできません: 同名のファイルがあります",
    },
    "scanned": {"en": "Scanned {count} files", "ja": "{count} 個のファイルを走査しました"},
    "using_config": {"en": "Using config: {path}", "ja": "設定ファイル: {path}"},
    "houdini_written": {
        "en": "Wrote Houdini environment snippet: {path}",
        "ja": "Houdini の環境変数の設定を書き出しました: {path}",
    },
}


def resolve_language(option: str | None, env: Mapping[str, str]) -> str:
    """言語を決める。`--lang`(`ja` / `en`)> `PIPEINIT_LANG` > `LANG`(`ja` で始まれば日本語)> 英語。"""
    for candidate in (option, env.get("PIPEINIT_LANG")):
        if candidate in SUPPORTED_LANGUAGES:
            return candidate
    locale = env.get("LC_ALL") or env.get("LC_MESSAGES") or env.get("LANG") or ""
    return "ja" if locale.lower().startswith("ja") else "en"


def translate(key: str, lang: str, **params: object) -> str:
    return CATALOG[key][lang].format(**params)
