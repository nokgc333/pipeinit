"""CLI のオプション(--json / --quiet / --verbose / --no-color / --lang / completion)と、メッセージの切り替えのテスト。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from pipeinit.cli import main
from pipeinit.exit_codes import EXIT_CODE_TABLE, exit_code_help
from pipeinit.messages import CATALOG, SUPPORTED_LANGUAGES, resolve_language, translate
from pipeinit.presenter import Printer, color_enabled

RULE = """schema_version: 1
project_type: x
folder_template: []
naming_patterns:
  - pattern: '^SHOT\\d{3}\\.hip$'
    description: "shot file"
"""


def _target(tmp_path: Path, *names: str) -> tuple[Path, Path]:
    target = tmp_path / "t"
    target.mkdir()
    for name in names:
        (target / name).write_text("x")
    rule = tmp_path / "rule.yaml"
    rule.write_text(RULE, encoding="utf-8")
    return target, rule


class TestLanguage:
    def test_the_option_wins_over_the_environment(self) -> None:
        assert resolve_language("en", {"PIPEINIT_LANG": "ja", "LANG": "ja_JP.UTF-8"}) == "en"

    def test_pipeinit_lang_wins_over_lang(self) -> None:
        assert resolve_language(None, {"PIPEINIT_LANG": "en", "LANG": "ja_JP.UTF-8"}) == "en"

    @pytest.mark.parametrize(
        ("env", "expected"),
        [
            ({"LANG": "ja_JP.UTF-8"}, "ja"),
            ({"LC_ALL": "ja_JP.UTF-8", "LANG": "en_US.UTF-8"}, "ja"),
            ({"LANG": "en_US.UTF-8"}, "en"),
            ({"LANG": "C"}, "en"),
            ({}, "en"),
            ({"PIPEINIT_LANG": "fr", "LANG": "ja_JP"}, "ja"),
        ],
    )
    def test_the_locale_decides_when_nothing_is_set_explicitly(
        self, env: dict[str, str], expected: str
    ) -> None:
        assert resolve_language(None, env) == expected

    def test_every_message_exists_in_every_language(self) -> None:
        for key, translations in CATALOG.items():
            assert set(translations) == set(SUPPORTED_LANGUAGES), key

    def test_placeholders_match_between_languages(self) -> None:
        import re

        for key, translations in CATALOG.items():
            fields = {
                lang: set(re.findall(r"{(\w+)}", text)) for lang, text in translations.items()
            }
            assert fields["en"] == fields["ja"], key

    def test_translate_fills_in_the_parameters(self) -> None:
        assert translate("created_summary", "ja", created=2, skipped=1).startswith("2 個")

    def test_init_prints_in_japanese_with_lang_ja(self, tmp_path: Path) -> None:
        result = CliRunner().invoke(
            main, ["--lang", "ja", "init", "--type", "generic", "--path", str(tmp_path / "p")]
        )

        assert "個のフォルダを作成" in result.output
        assert "作成: assets" in result.output

    def test_the_environment_variable_switches_the_language(self, tmp_path: Path) -> None:
        result = CliRunner().invoke(
            main,
            ["init", "--type", "generic", "--path", str(tmp_path / "p")],
            env={"PIPEINIT_LANG": "ja"},
        )

        assert "個のフォルダを作成" in result.output

    def test_errors_use_the_selected_language_prefix(self, tmp_path: Path) -> None:
        (tmp_path / "plain.hip").write_text("x")

        result = CliRunner().invoke(main, ["--lang", "ja", "bump", str(tmp_path / "plain.hip")])

        assert result.output.startswith("エラー:")

    def test_violations_are_reported_in_japanese(self, tmp_path: Path) -> None:
        target, rule = _target(tmp_path, "bad.hip")

        result = CliRunner().invoke(
            main, ["--lang", "ja", "validate", str(target), "--rules", str(rule)]
        )

        assert "'bad.hip' は次の規則に合いません: shot file" in result.output

    def test_json_output_is_always_the_same_regardless_of_language(self, tmp_path: Path) -> None:
        target, rule = _target(tmp_path, "bad.hip")
        args = ["validate", str(target), "--rules", str(rule), "--json"]

        english = CliRunner().invoke(main, ["--lang", "en", *args]).output
        japanese = CliRunner().invoke(main, ["--lang", "ja", *args]).output

        assert english == japanese
        assert "does not match" in json.loads(english)["violations"][0]["message"]


class TestJson:
    def test_validate_json_flag_equals_format_json(self, tmp_path: Path) -> None:
        target, rule = _target(tmp_path, "bad.hip")
        base = ["validate", str(target), "--rules", str(rule)]

        short = CliRunner().invoke(main, [*base, "--json"]).output
        long = CliRunner().invoke(main, [*base, "--format", "json"]).output

        assert short == long

    def test_init_json_lists_created_and_skipped(self, tmp_path: Path) -> None:
        target = str(tmp_path / "p")
        CliRunner().invoke(main, ["init", "--type", "generic", "--path", target])

        result = CliRunner().invoke(main, ["init", "--type", "generic", "--path", target, "--json"])

        payload = json.loads(result.output)
        assert payload["created"] == []
        assert payload["skipped"] == ["assets", "shots", "renders"]

    def test_bump_json_reports_whether_it_was_applied(self, tmp_path: Path) -> None:
        (tmp_path / "a_v001.hip").write_text("x")

        dry = json.loads(
            CliRunner().invoke(main, ["bump", str(tmp_path / "a_v001.hip"), "--json"]).output
        )
        done = json.loads(
            CliRunner()
            .invoke(main, ["bump", str(tmp_path / "a_v001.hip"), "--apply", "--json"])
            .output
        )

        assert dry == {"old": "a_v001.hip", "new": "a_v002.hip", "applied": False}
        assert done["applied"] is True

    def test_json_goes_to_stdout_only_and_errors_to_stderr(self, tmp_path: Path) -> None:
        result = CliRunner().invoke(main, ["validate", str(tmp_path), "--json"])

        assert json.loads(result.stdout)["count"] == 0
        assert result.stderr == ""


class TestQuietAndVerbose:
    def test_quiet_hides_the_init_summary_but_keeps_the_exit_code(self, tmp_path: Path) -> None:
        result = CliRunner().invoke(
            main, ["--quiet", "init", "--type", "generic", "--path", str(tmp_path / "p")]
        )

        assert result.exit_code == 0
        assert result.output == ""

    def test_quiet_still_prints_the_violations_themselves(self, tmp_path: Path) -> None:
        target, rule = _target(tmp_path, "bad.hip")

        result = CliRunner().invoke(main, ["-q", "validate", str(target), "--rules", str(rule)])

        assert result.exit_code == 1
        assert "bad.hip" in result.output

    def test_quiet_hides_the_no_violations_message(self, tmp_path: Path) -> None:
        target, rule = _target(tmp_path, "SHOT010.hip")

        result = CliRunner().invoke(main, ["-q", "validate", str(target), "--rules", str(rule)])

        assert result.exit_code == 0
        assert result.output == ""

    def test_errors_are_shown_even_when_quiet(self, tmp_path: Path) -> None:
        (tmp_path / "plain.hip").write_text("x")

        result = CliRunner().invoke(main, ["-q", "bump", str(tmp_path / "plain.hip")])

        assert "does not match" in result.output

    def test_verbose_details_go_to_stderr_not_stdout(self) -> None:
        printer = Printer(verbose=True)

        runner = CliRunner()

        @__import__("click").command()
        def probe() -> None:
            printer.detail("detail line")
            printer.result("result line")

        result = runner.invoke(probe)

        assert result.stdout == "result line\n"
        assert result.stderr == "detail line\n"

    def test_details_are_hidden_without_verbose_or_when_quiet(self) -> None:
        import click

        for printer in (Printer(), Printer(verbose=True, quiet=True)):

            @click.command()
            def probe(p: Printer = printer) -> None:
                p.detail("detail line")

            assert CliRunner().invoke(probe).output == ""


class TestColor:
    def test_no_color_option_or_the_environment_variable_turns_color_off(self) -> None:
        assert color_enabled(False, {}) is True
        assert color_enabled(True, {}) is False
        assert color_enabled(False, {"NO_COLOR": "1"}) is False
        assert color_enabled(False, {"NO_COLOR": ""}) is True

    def test_color_codes_are_added_only_when_enabled(self) -> None:
        assert "\x1b[" in Printer(color=True)._style("x", "red")
        assert Printer(color=False)._style("x", "red") == "x"

    def test_the_error_prefix_has_no_escape_codes_with_no_color(self, tmp_path: Path) -> None:
        (tmp_path / "plain.hip").write_text("x")

        result = CliRunner().invoke(main, ["--no-color", "bump", str(tmp_path / "plain.hip")])

        assert "\x1b[" not in result.output


class TestValidateTargets:
    def test_a_single_file_is_checked_by_its_name(self, tmp_path: Path) -> None:
        target, rule = _target(tmp_path, "bad.hip", "SHOT010.hip")

        bad = CliRunner().invoke(main, ["validate", str(target / "bad.hip"), "--rules", str(rule)])
        good = CliRunner().invoke(
            main, ["validate", str(target / "SHOT010.hip"), "--rules", str(rule)]
        )

        assert (bad.exit_code, good.exit_code) == (1, 0)

    def test_several_paths_are_reported_together(self, tmp_path: Path) -> None:
        target, rule = _target(tmp_path, "bad.hip", "worse.hip")

        result = CliRunner().invoke(
            main,
            [
                "validate",
                str(target / "bad.hip"),
                str(target / "worse.hip"),
                "--rules",
                str(rule),
                "--json",
            ],
        )

        assert json.loads(result.output)["count"] == 2

    def test_a_missing_path_is_a_usage_error(self, tmp_path: Path) -> None:
        result = CliRunner().invoke(main, ["validate", str(tmp_path / "none")])

        assert result.exit_code == 2

    def test_no_path_at_all_is_a_usage_error(self) -> None:
        assert CliRunner().invoke(main, ["validate"]).exit_code == 2


class TestHelpAndCompletion:
    def test_the_help_ends_with_the_exit_code_table(self) -> None:
        result = CliRunner().invoke(main, ["--help"])

        for code, _, _ in EXIT_CODE_TABLE:
            assert f"  {code}  " in result.output

    def test_the_table_is_available_in_both_languages(self) -> None:
        assert "Exit codes:" in exit_code_help("en")
        assert "終了コード:" in exit_code_help("ja")

    @pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
    def test_a_completion_script_is_printed_for_each_shell(self, shell: str) -> None:
        result = CliRunner().invoke(main, ["completion", shell])

        assert result.exit_code == 0
        assert "_PIPEINIT_COMPLETE" in result.output
        assert "pipeinit" in result.output

    def test_an_unknown_shell_is_refused(self) -> None:
        assert CliRunner().invoke(main, ["completion", "powershell"]).exit_code == 2
