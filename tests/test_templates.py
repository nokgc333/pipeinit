"""templates.py の単体テスト（TC-001〜006）。"""

from pathlib import Path

import pytest

from pipeinit.templates import PathTraversalError, generate_tree, resolve_safe_path


def test_resolve_safe_path_within_base_succeeds(tmp_path: Path) -> None:
    result = resolve_safe_path(tmp_path, "assets/characters")
    assert result == (tmp_path / "assets/characters").resolve()


def test_resolve_safe_path_escaping_base_raises(tmp_path: Path) -> None:
    """TC-005: '../' でベースディレクトリの外側を指す場合はPathTraversalError。"""
    with pytest.raises(PathTraversalError, match="escapes the target directory"):
        resolve_safe_path(tmp_path, "../../etc")


def test_generate_tree_creates_all_folders(tmp_path: Path) -> None:
    """TC-001: 空ディレクトリに対して全フォルダがcreatedとして生成される。"""
    rule = {
        "folder_template": [
            {"path": "assets/characters", "required": True},
            {"path": "shots", "required": True},
        ]
    }

    created, skipped = generate_tree(rule, tmp_path)

    assert (tmp_path / "assets/characters").is_dir()
    assert (tmp_path / "shots").is_dir()
    assert set(created) == {"assets/characters", "shots"}
    assert skipped == []


def test_generate_tree_is_idempotent(tmp_path: Path) -> None:
    """TC-002: 同一コマンドを2回実行しても2回目は全てskippedになる。"""
    rule = {"folder_template": [{"path": "shots", "required": True}]}

    generate_tree(rule, tmp_path)
    created_2nd, skipped_2nd = generate_tree(rule, tmp_path)

    assert created_2nd == []
    assert skipped_2nd == ["shots"]


def test_generate_tree_empty_template_succeeds(tmp_path: Path) -> None:
    """TC-006: folder_templateが空配列でもエラーにせず正常終了する。"""
    created, skipped = generate_tree({"folder_template": []}, tmp_path)

    assert created == []
    assert skipped == []


def test_generate_tree_rejects_path_traversal(tmp_path: Path) -> None:
    """TC-005: folder_templateにパストラバーサルが含まれる場合、何も作成せず例外を送出する。"""
    rule = {"folder_template": [{"path": "../../etc", "required": True}]}

    with pytest.raises(PathTraversalError):
        generate_tree(rule, tmp_path)
