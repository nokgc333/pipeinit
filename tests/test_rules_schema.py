"""ルール YAML のスキーマ検証のテスト(不正な値は、原因つきのエラーにする)。"""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeinit.rules import RuleFileError, load_rule_file

VALID = """
schema_version: 1
project_type: game
folder_template:
  - path: "shots"
    required: true
naming_patterns:
  - pattern: '^SHOT\\d{3}\\.hip$'
    description: "shot"
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "rule.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def _error(tmp_path: Path, text: str) -> str:
    with pytest.raises(RuleFileError) as info:
        load_rule_file(_write(tmp_path, text))
    return str(info.value)


def test_a_valid_rule_is_loaded(tmp_path: Path) -> None:
    rule = load_rule_file(_write(tmp_path, VALID))

    assert rule["project_type"] == "game"


def test_an_unsupported_schema_version_is_refused(tmp_path: Path) -> None:
    assert "schema_version" in _error(
        tmp_path, VALID.replace("schema_version: 1", "schema_version: 2")
    )


def test_a_string_schema_version_is_refused(tmp_path: Path) -> None:
    assert "schema_version" in _error(
        tmp_path, VALID.replace("schema_version: 1", 'schema_version: "1"')
    )


@pytest.mark.parametrize("value", ["42", "{}", "null", "text"])
def test_folder_template_must_be_a_list_of_mappings(tmp_path: Path, value: str) -> None:
    text = VALID.split("folder_template:")[0] + f"folder_template: {value}\nnaming_patterns: []\n"

    assert "folder_template" in _error(tmp_path, text)


def test_an_empty_folder_template_is_allowed(tmp_path: Path) -> None:
    text = VALID.split("folder_template:")[0] + "folder_template: []\nnaming_patterns: []\n"

    assert load_rule_file(_write(tmp_path, text))["folder_template"] == []


def test_a_folder_entry_without_a_path_is_refused_with_its_position(tmp_path: Path) -> None:
    text = VALID.replace('  - path: "shots"\n    required: true', "  - required: true")

    message = _error(tmp_path, text)

    assert "folder_template[0]" in message
    assert "path" in message


@pytest.mark.parametrize("path", ['""', "123", "[a]"])
def test_a_folder_path_must_be_a_non_empty_string(tmp_path: Path, path: str) -> None:
    message = _error(tmp_path, VALID.replace('path: "shots"', f"path: {path}"))

    assert "folder_template[0].path" in message


@pytest.mark.parametrize("path", ["/etc/x", "C:\\\\x", "\\\\\\\\server\\\\share"])
def test_an_absolute_folder_path_is_refused(tmp_path: Path, path: str) -> None:
    message = _error(tmp_path, VALID.replace('path: "shots"', f'path: "{path}"'))

    assert "relative" in message


def test_a_folder_path_with_a_null_byte_is_refused(tmp_path: Path) -> None:
    message = _error(tmp_path, VALID.replace('path: "shots"', 'path: "a\\0b"'))

    assert "folder_template[0].path" in message


def test_a_pattern_that_is_not_a_valid_regex_is_refused_with_the_reason(tmp_path: Path) -> None:
    message = _error(tmp_path, VALID.replace("'^SHOT\\d{3}\\.hip$'", "'(unclosed'"))

    assert "naming_patterns[0].pattern" in message
    assert "regular expression" in message


def test_a_pattern_entry_needs_a_pattern_and_a_description(tmp_path: Path) -> None:
    no_description = VALID.replace('    description: "shot"\n', "")
    no_pattern = VALID.replace(
        "  - pattern: '^SHOT\\d{3}\\.hip$'\n    description", "  - description"
    )

    assert "naming_patterns[0].description" in _error(tmp_path, no_description)
    assert "naming_patterns[0].pattern" in _error(tmp_path, no_pattern)


def test_the_error_names_the_file(tmp_path: Path) -> None:
    assert "rule.yaml" in _error(tmp_path, "schema_version: 2\n")


def test_a_file_that_cannot_be_read_as_text_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "rule.yaml"
    path.write_bytes(b"\xff\xfe\x00bad")

    with pytest.raises(RuleFileError, match="could not be read"):
        load_rule_file(path)


def test_a_directory_instead_of_a_file_is_reported(tmp_path: Path) -> None:
    with pytest.raises(RuleFileError, match="could not be read"):
        load_rule_file(tmp_path)


def test_python_object_tags_are_not_executed(tmp_path: Path) -> None:
    text = "!!python/object/apply:os.system ['echo pwned']\n"

    with pytest.raises(RuleFileError):
        load_rule_file(_write(tmp_path, text))


def test_the_bundled_rules_are_all_valid() -> None:
    from pipeinit.rules import bundled_rule_path

    for name in ("game", "film", "generic"):
        assert load_rule_file(bundled_rule_path(name))["project_type"] == name
