"""設定ファイルの自動検出・ユーザー設定・Houdini の環境変数のスニペットのテスト。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from pipeinit.cli import main
from pipeinit.config import (
    PROJECT_CONFIG_NAME,
    ConfigError,
    Settings,
    discover_settings,
    find_project_config,
    load_config,
    user_config_path,
)
from pipeinit.houdini_env import (
    ENV_SNIPPET_NAME,
    houdini_env_snippet,
    write_houdini_env_snippet,
)

RULE = """schema_version: 1
project_type: x
folder_template: []
naming_patterns:
  - pattern: '^OK\\.txt$'
    description: "only OK.txt"
"""


def _config(directory: Path, **values: str) -> Path:
    path = directory / PROJECT_CONFIG_NAME
    path.write_text(yaml.safe_dump(values), encoding="utf-8")
    return path


class TestFindProjectConfig:
    def test_it_is_found_in_the_start_folder(self, tmp_path: Path) -> None:
        config = _config(tmp_path, lang="en")

        assert find_project_config(tmp_path) == config.resolve()

    def test_it_is_found_in_a_parent_folder(self, tmp_path: Path) -> None:
        config = _config(tmp_path, lang="en")
        deep = tmp_path / "a" / "b"
        deep.mkdir(parents=True)

        assert find_project_config(deep) == config.resolve()

    def test_the_nearest_one_wins(self, tmp_path: Path) -> None:
        _config(tmp_path, lang="en")
        inner = tmp_path / "inner"
        inner.mkdir()
        nearest = _config(inner, lang="ja")

        assert find_project_config(inner) == nearest.resolve()

    def test_none_is_returned_when_there_is_no_config(self, tmp_path: Path) -> None:
        assert (
            find_project_config(tmp_path) is None
            or find_project_config(tmp_path) != tmp_path / PROJECT_CONFIG_NAME
        )


class TestUserConfigPath:
    def test_xdg_config_home_is_used_first(self) -> None:
        assert user_config_path({"XDG_CONFIG_HOME": "/x", "HOME": "/h"}, "linux") == Path(
            "/x/pipeinit/config.yaml"
        )

    def test_home_dot_config_is_the_fallback(self) -> None:
        assert user_config_path({"HOME": "/h"}, "darwin") == Path("/h/.config/pipeinit/config.yaml")

    def test_windows_uses_appdata(self) -> None:
        assert user_config_path({"APPDATA": "C:/Users/a/AppData/Roaming"}, "win32") == Path(
            "C:/Users/a/AppData/Roaming/pipeinit/config.yaml"
        )

    def test_without_any_variable_there_is_no_path(self) -> None:
        assert user_config_path({}, "linux") is None
        assert user_config_path({}, "win32") is None


class TestLoadConfig:
    def test_known_keys_are_read_and_the_rules_path_is_made_absolute(self, tmp_path: Path) -> None:
        config = _config(tmp_path, rules="my_rules.yaml", lang="ja", project_type="maya")

        settings = load_config(config)

        assert settings.rules == str((tmp_path / "my_rules.yaml").resolve())
        assert (settings.lang, settings.project_type) == ("ja", "maya")
        assert settings.source == config

    def test_an_empty_file_gives_empty_settings(self, tmp_path: Path) -> None:
        path = tmp_path / PROJECT_CONFIG_NAME
        path.write_text("", encoding="utf-8")

        assert load_config(path) == Settings(source=path)

    @pytest.mark.parametrize(
        ("content", "message"),
        [
            ("- a\n- b\n", "must be a YAML mapping"),
            ("colour: red\n", "unknown key"),
            ("lang: fr\n", "lang must be one of"),
            ("rules: 5\n", "rules must be a non-empty string"),
            ("lang: ''\n", "non-empty string"),
            ("a: [unclosed\n", "could not be read"),
        ],
    )
    def test_bad_configs_are_refused_with_the_reason(
        self, tmp_path: Path, content: str, message: str
    ) -> None:
        path = tmp_path / PROJECT_CONFIG_NAME
        path.write_text(content, encoding="utf-8")

        with pytest.raises(ConfigError, match=message):
            load_config(path)


class TestDiscoverSettings:
    def test_the_project_config_wins_over_the_user_config(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        (home / ".config" / "pipeinit").mkdir(parents=True)
        (home / ".config" / "pipeinit" / "config.yaml").write_text("lang: ja\n")
        project = tmp_path / "project"
        project.mkdir()
        _config(project, lang="en")

        settings = discover_settings(project, {"HOME": str(home)})

        assert settings.lang == "en"

    def test_the_user_config_fills_in_what_the_project_does_not_set(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        (home / ".config" / "pipeinit").mkdir(parents=True)
        (home / ".config" / "pipeinit" / "config.yaml").write_text(
            "lang: ja\nproject_type: unreal\n"
        )
        project = tmp_path / "project"
        project.mkdir()
        _config(project, project_type="maya")

        settings = discover_settings(project, {"HOME": str(home)})

        assert (settings.lang, settings.project_type) == ("ja", "maya")

    def test_the_user_config_alone_is_used_when_there_is_no_project_config(
        self, tmp_path: Path
    ) -> None:
        home = tmp_path / "home"
        (home / ".config" / "pipeinit").mkdir(parents=True)
        (home / ".config" / "pipeinit" / "config.yaml").write_text("lang: ja\n")
        empty = tmp_path / "empty"
        empty.mkdir()

        assert discover_settings(empty, {"HOME": str(home)}).lang == "ja"

    def test_no_config_anywhere_gives_empty_settings(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()

        assert discover_settings(empty, {"HOME": str(tmp_path / "nohome")}).rules is None


class TestCliUsesTheConfig:
    def test_validate_uses_the_rules_from_the_project_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "rules.yaml").write_text(RULE, encoding="utf-8")
        _config(tmp_path, rules="rules.yaml")
        (tmp_path / "scan").mkdir()
        (tmp_path / "scan" / "OK.txt").write_text("x")
        (tmp_path / "scan" / "bad.txt").write_text("x")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "nohome"))

        result = CliRunner().invoke(main, ["--lang", "en", "validate", "scan", "--json"])

        assert [v["file"] for v in json.loads(result.output)["violations"]] == ["bad.txt"]

    def test_the_rules_option_overrides_the_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "rules.yaml").write_text(RULE, encoding="utf-8")
        _config(tmp_path, rules="rules.yaml")
        (tmp_path / "scan").mkdir()
        (tmp_path / "scan" / "bad.txt").write_text("x")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "nohome"))

        result = CliRunner().invoke(main, ["validate", "scan", "--json"])
        generic = CliRunner().invoke(
            main,
            ["validate", "scan", "--json", "--rules", str(_generic())],
        )

        assert json.loads(result.output)["count"] == 1
        assert json.loads(generic.output)["count"] == 1

    def test_init_takes_the_project_type_from_the_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _config(tmp_path, project_type="blender")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "nohome"))

        result = CliRunner().invoke(main, ["init", "--path", str(tmp_path / "out")])

        assert result.exit_code == 0
        assert (tmp_path / "out" / "blend").is_dir()

    def test_init_without_a_type_anywhere_is_a_usage_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "nohome"))

        result = CliRunner().invoke(main, ["init", "--path", str(tmp_path / "out")])

        assert result.exit_code == 2
        assert "--type" in result.output

    def test_the_type_option_overrides_the_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _config(tmp_path, project_type="blender")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "nohome"))

        CliRunner().invoke(main, ["init", "--type", "maya", "--path", str(tmp_path / "out")])

        assert (tmp_path / "out" / "scenes").is_dir()

    def test_a_config_with_an_unknown_project_type_is_a_usage_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _config(tmp_path, project_type="lightwave")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "nohome"))

        result = CliRunner().invoke(main, ["init", "--path", str(tmp_path / "out")])

        assert result.exit_code == 2
        assert "lightwave" in result.output

    def test_the_language_comes_from_the_config_but_the_option_wins(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _config(tmp_path, lang="ja")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "nohome"))
        monkeypatch.delenv("PIPEINIT_LANG", raising=False)

        japanese = CliRunner().invoke(
            main, ["init", "--type", "generic", "--path", str(tmp_path / "a")]
        )
        english = CliRunner().invoke(
            main, ["--lang", "en", "init", "--type", "generic", "--path", str(tmp_path / "b")]
        )

        assert "個のフォルダを作成" in japanese.output
        assert "Created" in english.output

    def test_a_broken_config_stops_the_command_with_its_reason(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / PROJECT_CONFIG_NAME).write_text("colour: red\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "nohome"))

        result = CliRunner().invoke(main, ["validate", str(tmp_path)])

        assert result.exit_code != 0
        assert "unknown key" in result.output

    def test_verbose_says_which_config_is_used_on_stderr(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _config(tmp_path, lang="en")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "nohome"))

        result = CliRunner().invoke(main, ["-v", "validate", str(tmp_path), "--json"])

        assert "Using config:" in result.stderr
        assert "Using config" not in result.stdout


def _generic() -> Path:
    from pipeinit.rules import bundled_rule_path

    return bundled_rule_path("generic")


class TestHoudiniEnv:
    def test_the_snippet_sets_job_with_forward_slashes(self, tmp_path: Path) -> None:
        text = houdini_env_snippet(tmp_path)

        assert f'JOB = "{tmp_path.resolve().as_posix()}"' in text
        assert "\\" not in text

    def test_hip_is_not_set_because_houdini_decides_it_from_the_scene(self, tmp_path: Path) -> None:
        assert "HIP" not in houdini_env_snippet(tmp_path)

    def test_the_file_is_written_once_and_never_overwritten(self, tmp_path: Path) -> None:
        first = write_houdini_env_snippet(tmp_path)
        first.write_text("edited by the artist\n")

        second = write_houdini_env_snippet(tmp_path)

        assert second == first == tmp_path / ENV_SNIPPET_NAME
        assert second.read_text() == "edited by the artist\n"

    def test_init_writes_the_snippet_with_the_flag(self, tmp_path: Path) -> None:
        target = tmp_path / "proj"

        result = CliRunner().invoke(
            main,
            ["--lang", "en", "init", "--type", "houdini", "--path", str(target), "--houdini-env"],
        )

        assert result.exit_code == 0
        assert "Wrote Houdini environment snippet" in result.output
        assert (target / ENV_SNIPPET_NAME).read_text().startswith("# PipeInit")

    def test_init_does_not_write_it_without_the_flag(self, tmp_path: Path) -> None:
        target = tmp_path / "proj"

        CliRunner().invoke(main, ["init", "--type", "houdini", "--path", str(target)])

        assert not (target / ENV_SNIPPET_NAME).exists()

    def test_init_json_reports_the_snippet_path(self, tmp_path: Path) -> None:
        target = tmp_path / "proj"

        result = CliRunner().invoke(
            main, ["init", "--type", "houdini", "--path", str(target), "--houdini-env", "--json"]
        )

        assert json.loads(result.output)["houdini_env"].endswith(ENV_SNIPPET_NAME)


class TestSuggestionsAndHook:
    def test_validate_prints_a_rename_candidate_and_never_renames(self, tmp_path: Path) -> None:
        scan = tmp_path / "scan"
        scan.mkdir()
        (scan / "shot010_lighting_v3.hip").write_text("x")

        result = CliRunner().invoke(
            main,
            ["--lang", "en", "validate", str(scan), "--rules", str(_game())],
        )

        assert "suggestion: SHOT010_lighting_v003.hip" in result.output
        assert (scan / "shot010_lighting_v3.hip").exists()
        assert not (scan / "SHOT010_lighting_v003.hip").exists()

    def test_the_json_carries_the_suggestion(self, tmp_path: Path) -> None:
        scan = tmp_path / "scan"
        scan.mkdir()
        (scan / "shot010_lighting_v3.hip").write_text("x")

        result = CliRunner().invoke(
            main, ["validate", str(scan), "--rules", str(_game()), "--json"]
        )

        assert (
            json.loads(result.output)["violations"][0]["suggestion"] == "SHOT010_lighting_v003.hip"
        )

    def test_the_precommit_hook_runs_validate_on_the_filenames(self) -> None:
        hooks = yaml.safe_load(
            (Path(__file__).resolve().parents[1] / ".pre-commit-hooks.yaml").read_text()
        )

        hook = hooks[0]
        assert hook["id"] == "pipeinit-validate"
        assert hook["entry"] == "pipeinit validate"
        assert hook["pass_filenames"] is True
        assert hook["language"] == "python"


def _game() -> Path:
    from pipeinit.rules import bundled_rule_path

    return bundled_rule_path("game")


def test_the_snippet_does_not_count_as_a_naming_violation(tmp_path: Path) -> None:
    target = tmp_path / "proj"
    CliRunner().invoke(main, ["init", "--type", "houdini", "--path", str(target), "--houdini-env"])

    result = CliRunner().invoke(
        main,
        ["validate", str(target), "--rules", str(_houdini()), "--json"],
    )

    assert json.loads(result.output)["count"] == 0


def _houdini() -> Path:
    from pipeinit.rules import bundled_rule_path

    return bundled_rule_path("houdini")
