"""rules.py の単体テスト（TC-018〜021）。"""

from pathlib import Path

import pytest

from pipeinit.rules import RuleFileError, load_rule_file


def _write_yaml(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_load_rule_file_returns_parsed_mapping(tmp_path: Path) -> None:
    """TC-018: 正常なYAMLはdictとして読み込める。"""
    path = _write_yaml(
        tmp_path,
        "game.yaml",
        """
        schema_version: 1
        project_type: game
        folder_template:
          - path: "assets/characters"
            required: true
        naming_patterns:
          - pattern: '^SHOT\\d{3}\\.hip$'
            description: "shot file"
        """,
    )

    rule = load_rule_file(path)

    assert rule["project_type"] == "game"
    assert rule["folder_template"][0]["path"] == "assets/characters"


def test_load_rule_file_missing_required_key_raises_with_key_name(tmp_path: Path) -> None:
    """TC-019: 必須キー欠落時、欠落キー名がエラーメッセージに含まれる。"""
    path = _write_yaml(
        tmp_path,
        "broken.yaml",
        """
        schema_version: 1
        project_type: game
        folder_template: []
        """,
    )

    with pytest.raises(RuleFileError, match="naming_patterns"):
        load_rule_file(path)


def test_load_rule_file_invalid_yaml_syntax_raises(tmp_path: Path) -> None:
    """TC-020: 構文的に壊れたYAMLはRuleFileErrorになる。"""
    path = _write_yaml(tmp_path, "syntax_error.yaml", "key: [unclosed")

    with pytest.raises(RuleFileError):
        load_rule_file(path)


def test_load_rule_file_non_mapping_top_level_raises(tmp_path: Path) -> None:
    """トップレベルがマッピングでない場合もRuleFileError。"""
    path = _write_yaml(tmp_path, "list.yaml", "- 1\n- 2\n")

    with pytest.raises(RuleFileError, match="mapping"):
        load_rule_file(path)
