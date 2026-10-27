"""Houdini の環境変数 `$JOB`(プロジェクトのルート)を設定するスニペットを作る。

`houdini.env`(ユーザーの設定フォルダ)に追記して使う。環境ファイルは `NAME = 値` の形式で、
パスは区切りを `/` にする(Windows でも使える)。

`$HIP` は、開いたシーンの場所から Houdini が決める組み込みの変数で、環境ファイルでは変えられない
(Houdini 22.0.466 で確認、docs/sample-verification.md)ため、設定しない。
"""

from __future__ import annotations

from pathlib import Path

ENV_SNIPPET_NAME = ".pipeinit/houdini.env"


def _posix(path: Path) -> str:
    return path.resolve().as_posix()


def houdini_env_snippet(project_root: Path) -> str:
    root = project_root.resolve()
    lines = [
        "# PipeInit: プロジェクトの環境変数。Houdini の houdini.env に追記する。",
        f'JOB = "{_posix(root)}"',
    ]
    return "\n".join(lines) + "\n"


def write_houdini_env_snippet(project_root: Path) -> Path:
    """プロジェクト直下の `.pipeinit/` にスニペットを書く(隠しフォルダなので、命名の検査の対象にならない)。

    すでにあるときは、上書きせずにそのまま返す。
    """
    target = project_root / ENV_SNIPPET_NAME
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(houdini_env_snippet(project_root), encoding="utf-8")
    return target
