"""ファイル操作の安全な部品(上書きしない改名、シンボリックリンクを辿らない走査)。"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path


class DestinationExistsError(FileExistsError):
    """改名先に、すでに同名のファイル・フォルダがある。"""


def rename_without_overwrite(source: Path, destination: Path) -> None:
    """改名先がすでにあれば、上書きせずに DestinationExistsError を送出する。

    「存在を確かめてから改名する」と、確認と改名の間に同名のファイルができたとき、
    POSIX の `rename` は黙って上書きする。ハードリンクの作成は、先がすでにあると
    原子的に失敗するので、リンクを作ってから元の名前を消す。ハードリンクが使えない
    ファイルシステムでは、(Windows の `rename` と同じく、先があれば失敗する)改名にする。
    """
    try:
        os.link(source, destination)
    except FileExistsError as exc:
        raise DestinationExistsError(str(destination)) from exc
    except OSError:
        if destination.exists() or destination.is_symlink():
            raise DestinationExistsError(str(destination)) from None
        source.rename(destination)
        return
    os.unlink(source)


def iter_files(target: Path) -> Iterator[Path]:
    """target 配下のファイルを、決まった順序で 1 つずつ返す(全件をメモリに持たない)。

    - 隠しファイル・隠しフォルダ(`.` で始まる名前)は、辿らない
    - シンボリックリンクのフォルダは辿らない(循環と、外への脱出を避ける)
    - シンボリックリンクのファイルは、リンクの名前で検査する(中身は読まない)
    """
    stack = [target]
    while stack:
        directory = stack.pop()
        try:
            with os.scandir(directory) as entries:
                children = sorted(entries, key=lambda entry: entry.name)
        except OSError:
            continue
        subdirectories: list[Path] = []
        for entry in children:
            if entry.name.startswith("."):
                continue
            if entry.is_dir(follow_symlinks=False):
                subdirectories.append(Path(entry.path))
            elif entry.is_dir():
                continue
            else:
                yield Path(entry.path)
        stack.extend(reversed(subdirectories))
