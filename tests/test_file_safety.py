"""ファイル操作の安全性のテスト(上書き・パストラバーサル・シンボリックリンク・権限)。"""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from pipeinit.cli import (
    EXIT_NOT_WRITABLE,
    EXIT_PATH_TRAVERSAL,
    EXIT_RENAME_CONFLICT,
    main,
)
from pipeinit.fsutil import DestinationExistsError, iter_files, rename_without_overwrite
from pipeinit.templates import PathTraversalError, generate_tree, resolve_safe_path

POSIX_ONLY = pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions and symlinks")


class TestRenameWithoutOverwrite:
    def test_the_file_is_renamed_when_the_destination_is_free(self, tmp_path: Path) -> None:
        source = tmp_path / "a_v001.hip"
        source.write_text("one")

        rename_without_overwrite(source, tmp_path / "a_v002.hip")

        assert not source.exists()
        assert (tmp_path / "a_v002.hip").read_text() == "one"

    def test_an_existing_destination_is_never_overwritten(self, tmp_path: Path) -> None:
        source = tmp_path / "a_v001.hip"
        destination = tmp_path / "a_v002.hip"
        source.write_text("new")
        destination.write_text("precious")

        with pytest.raises(DestinationExistsError):
            rename_without_overwrite(source, destination)

        assert destination.read_text() == "precious"
        assert source.read_text() == "new"

    @POSIX_ONLY
    def test_a_destination_that_is_a_dangling_symlink_counts_as_existing(
        self, tmp_path: Path
    ) -> None:
        source = tmp_path / "a_v001.hip"
        source.write_text("x")
        (tmp_path / "a_v002.hip").symlink_to(tmp_path / "nowhere")

        with pytest.raises(DestinationExistsError):
            rename_without_overwrite(source, tmp_path / "a_v002.hip")

        assert source.exists()

    def test_a_destination_created_at_the_last_moment_is_kept(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        source = tmp_path / "a_v001.hip"
        destination = tmp_path / "a_v002.hip"
        source.write_text("new")
        real_link = os.link

        def racing_link(src: Path, dst: Path) -> None:
            destination.write_text("created by someone else")
            real_link(src, dst)

        monkeypatch.setattr(os, "link", racing_link)

        with pytest.raises(DestinationExistsError):
            rename_without_overwrite(source, destination)

        assert destination.read_text() == "created by someone else"
        assert source.read_text() == "new"

    def test_without_hard_links_an_existing_destination_still_wins(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        source = tmp_path / "a_v001.hip"
        destination = tmp_path / "a_v002.hip"
        source.write_text("new")
        destination.write_text("precious")

        def no_links(src: Path, dst: Path) -> None:
            raise PermissionError("hard links are not supported here")

        monkeypatch.setattr(os, "link", no_links)

        with pytest.raises(DestinationExistsError):
            rename_without_overwrite(source, destination)

        assert destination.read_text() == "precious"

    def test_without_hard_links_a_free_destination_is_renamed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        source = tmp_path / "a_v001.hip"
        source.write_text("new")

        def no_links(src: Path, dst: Path) -> None:
            raise PermissionError("hard links are not supported here")

        monkeypatch.setattr(os, "link", no_links)

        rename_without_overwrite(source, tmp_path / "a_v002.hip")

        assert (tmp_path / "a_v002.hip").read_text() == "new"
        assert not source.exists()

    def test_a_missing_source_is_reported_as_an_os_error(self, tmp_path: Path) -> None:
        with pytest.raises(OSError):
            rename_without_overwrite(tmp_path / "none_v001.hip", tmp_path / "none_v002.hip")


class TestBumpCommand:
    def test_apply_refuses_to_overwrite_and_leaves_both_files(self, tmp_path: Path) -> None:
        (tmp_path / "a_v001.hip").write_text("old")
        (tmp_path / "a_v002.hip").write_text("keep me")

        result = CliRunner().invoke(main, ["bump", str(tmp_path / "a_v001.hip"), "--apply"])

        assert result.exit_code == EXIT_RENAME_CONFLICT
        assert (tmp_path / "a_v002.hip").read_text() == "keep me"
        assert (tmp_path / "a_v001.hip").exists()

    def test_the_default_is_a_dry_run_that_changes_nothing(self, tmp_path: Path) -> None:
        (tmp_path / "a_v001.hip").write_text("old")

        result = CliRunner().invoke(main, ["bump", str(tmp_path / "a_v001.hip")])

        assert result.exit_code == 0
        assert (tmp_path / "a_v001.hip").exists()
        assert not (tmp_path / "a_v002.hip").exists()

    @POSIX_ONLY
    def test_a_read_only_folder_is_reported_not_a_traceback(self, tmp_path: Path) -> None:
        folder = tmp_path / "locked"
        folder.mkdir()
        (folder / "a_v001.hip").write_text("x")
        folder.chmod(stat.S_IRUSR | stat.S_IXUSR)
        try:
            if os.access(folder, os.W_OK):
                pytest.skip("running as a user that ignores permissions")
            result = CliRunner().invoke(main, ["bump", str(folder / "a_v001.hip"), "--apply"])
        finally:
            folder.chmod(stat.S_IRWXU)

        assert result.exit_code == EXIT_NOT_WRITABLE
        assert "Traceback" not in result.output


class TestPathTraversal:
    @pytest.mark.parametrize("relative", ["../outside", "a/../../outside", "a/b/../../../x"])
    def test_a_path_that_climbs_out_is_refused(self, tmp_path: Path, relative: str) -> None:
        with pytest.raises(PathTraversalError):
            resolve_safe_path(tmp_path / "base", relative)

    def test_a_path_that_stays_inside_even_with_dotdot_is_allowed(self, tmp_path: Path) -> None:
        assert resolve_safe_path(tmp_path, "a/../b") == (tmp_path / "b").resolve()

    @POSIX_ONLY
    def test_a_symlink_inside_the_target_that_points_outside_is_refused(
        self, tmp_path: Path
    ) -> None:
        base = tmp_path / "base"
        outside = tmp_path / "outside"
        base.mkdir()
        outside.mkdir()
        (base / "link").symlink_to(outside)

        with pytest.raises(PathTraversalError):
            resolve_safe_path(base, "link/escaped")

    def test_nothing_is_created_when_any_entry_escapes(self, tmp_path: Path) -> None:
        base = tmp_path / "base"
        base.mkdir()
        rule = {"folder_template": [{"path": "ok"}, {"path": "../escape"}]}

        with pytest.raises(PathTraversalError):
            generate_tree(rule, base)

        assert list(base.iterdir()) == []
        assert not (tmp_path / "escape").exists()

    def test_init_with_a_bad_rule_through_the_cli_exits_with_the_traversal_code(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import pipeinit.cli as cli

        bad = tmp_path / "bad.yaml"
        bad.write_text(
            "schema_version: 1\nproject_type: x\nfolder_template:\n"
            '  - path: "a/../../escape"\nnaming_patterns: []\n',
            encoding="utf-8",
        )
        monkeypatch.setattr(cli, "bundled_rule_path", lambda name: bad)
        target = tmp_path / "target"

        result = CliRunner().invoke(main, ["init", "--type", "generic", "--path", str(target)])

        assert result.exit_code == EXIT_PATH_TRAVERSAL
        assert not (tmp_path / "escape").exists()

    @POSIX_ONLY
    def test_a_read_only_target_is_reported(self, tmp_path: Path) -> None:
        target = tmp_path / "locked"
        target.mkdir()
        target.chmod(stat.S_IRUSR | stat.S_IXUSR)
        try:
            if os.access(target, os.W_OK):
                pytest.skip("running as a user that ignores permissions")
            result = CliRunner().invoke(main, ["init", "--type", "generic", "--path", str(target)])
        finally:
            target.chmod(stat.S_IRWXU)

        assert result.exit_code == EXIT_NOT_WRITABLE

    def test_a_target_whose_parent_is_a_file_is_reported(self, tmp_path: Path) -> None:
        blocker = tmp_path / "file"
        blocker.write_text("x")

        result = CliRunner().invoke(
            main, ["init", "--type", "generic", "--path", str(blocker / "sub")]
        )

        assert result.exit_code == EXIT_NOT_WRITABLE
        assert "Traceback" not in result.output


class TestWalker:
    def _names(self, root: Path) -> list[str]:
        return [str(p.relative_to(root)) for p in iter_files(root)]

    def test_files_are_listed_in_a_stable_order(self, tmp_path: Path) -> None:
        for name in ("b.txt", "a.txt", "c/z.txt", "c/y.txt"):
            (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / name).write_text("x")

        assert self._names(tmp_path) == [
            "a.txt",
            "b.txt",
            str(Path("c/y.txt")),
            str(Path("c/z.txt")),
        ]

    def test_hidden_files_and_folders_are_skipped(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("x")
        (tmp_path / ".hidden.txt").write_text("x")
        (tmp_path / "shown.txt").write_text("x")

        assert self._names(tmp_path) == ["shown.txt"]

    @POSIX_ONLY
    def test_a_symlinked_folder_is_not_followed(self, tmp_path: Path) -> None:
        real = tmp_path / "real"
        real.mkdir()
        (real / "inside.txt").write_text("x")
        outside = tmp_path / "scan"
        outside.mkdir()
        (outside / "link").symlink_to(real, target_is_directory=True)

        assert self._names(outside) == []

    @POSIX_ONLY
    def test_a_symlink_loop_terminates(self, tmp_path: Path) -> None:
        scan = tmp_path / "scan"
        scan.mkdir()
        (scan / "loop").symlink_to(scan, target_is_directory=True)
        (scan / "file.txt").write_text("x")

        assert self._names(scan) == ["file.txt"]

    @POSIX_ONLY
    def test_a_symlinked_file_is_listed_by_its_own_name_even_when_dangling(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "dangling.txt").symlink_to(tmp_path / "nowhere")

        assert self._names(tmp_path) == ["dangling.txt"]

    @POSIX_ONLY
    def test_an_unreadable_folder_is_skipped_instead_of_failing_the_scan(
        self, tmp_path: Path
    ) -> None:
        locked = tmp_path / "locked"
        locked.mkdir()
        (locked / "x.txt").write_text("x")
        (tmp_path / "ok.txt").write_text("x")
        locked.chmod(0)
        try:
            if os.access(locked, os.R_OK):
                pytest.skip("running as a user that ignores permissions")
            names = self._names(tmp_path)
        finally:
            locked.chmod(stat.S_IRWXU)

        assert names == ["ok.txt"]

    def test_deep_trees_are_handled_without_recursion_limits(self, tmp_path: Path) -> None:
        deep = tmp_path
        for index in range(60):
            deep = deep / f"d{index}"
        deep.mkdir(parents=True)
        (deep / "leaf.txt").write_text("x")

        assert len(self._names(tmp_path)) == 1

    def test_japanese_spaces_and_case_differences_are_kept_as_they_are(
        self, tmp_path: Path
    ) -> None:
        for name in ("ショット 010.txt", "SHOT010.TXT", "shot010.txt"):
            (tmp_path / name).write_text("x")

        assert len(self._names(tmp_path)) == len({n for n in self._names(tmp_path)})
        assert "ショット 010.txt" in self._names(tmp_path)
