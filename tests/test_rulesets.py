"""DCC ごとのルールセット(Houdini / Maya / Blender / Unreal)のテスト。"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from pipeinit.cli import PROJECT_TYPES, main
from pipeinit.rules import bundled_rule_path, load_rule_file
from pipeinit.validator import validate_paths

ACCEPTED = {
    "houdini": [
        "SHOT010_fx_v003.hip",
        "SHOT010_fx_v001.hiplc",
        "Studio_Tornado_v001.hda",
        "SHOT010_fx_v003.bgeo.sc",
        "SHOT010_fx_v003.0001.exr",
    ],
    "maya": [
        "SHOT010_anim_v003.ma",
        "SHOT020_anim_v010.mb",
        "Character_Hero_v001.mb",
        "Hero_body_diffuse.png",
        "Character_Hero.fbx",
    ],
    "blender": [
        "SHOT010_layout_v003.blend",
        "Prop_Chair_v001.blend",
        "Chair_wood_basecolor.png",
        "Prop_Chair.glb",
    ],
    "unreal": [
        "SM_Chair_01.uasset",
        "T_Wood_D.uasset",
        "BP_Door.uasset",
        "L_Forest_Main.umap",
        "Chair.fbx",
    ],
}
REJECTED = {
    "houdini": ["shot010_fx_v003.hip", "SHOT010_fx.hip", "SHOT010_fx_v3.hip", "notes.txt"],
    "maya": ["SHOT010_anim_v003.hip", "SHOT010 anim v003.ma", "shot010_anim_v003.ma"],
    "blender": ["SHOT010_layout_v003.ma", "SHOT010_layout.blend"],
    "unreal": ["Chair.uasset", "sm_chair.uasset", "SM_Chair.fbx.uasset", "Forest.umap"],
}


def _check(tmp_path: Path, project_type: str, names: list[str]) -> list[str]:
    folder = tmp_path / project_type
    folder.mkdir(exist_ok=True)
    for name in names:
        (folder / name).write_text("x")
    rules = str(bundled_rule_path(project_type))
    return sorted(v["file"] for v in validate_paths([folder], rules))


@pytest.mark.parametrize("project_type", sorted(ACCEPTED))
def test_the_names_a_studio_would_use_are_accepted(tmp_path: Path, project_type: str) -> None:
    assert _check(tmp_path, project_type, ACCEPTED[project_type]) == []


@pytest.mark.parametrize("project_type", sorted(REJECTED))
def test_names_that_break_the_convention_are_reported(tmp_path: Path, project_type: str) -> None:
    names = REJECTED[project_type]

    assert _check(tmp_path, project_type, names) == sorted(names)


def test_a_maya_file_is_no_longer_a_violation_under_the_maya_ruleset(tmp_path: Path) -> None:
    assert _check(tmp_path, "maya", ["SHOT010_anim_v003.ma"]) == []


@pytest.mark.parametrize("project_type", ["houdini", "maya", "blender", "unreal"])
def test_every_new_ruleset_is_valid_and_declares_its_type(project_type: str) -> None:
    rule = load_rule_file(bundled_rule_path(project_type))

    assert rule["project_type"] == project_type
    assert len(rule["folder_template"]) >= 5
    assert len(rule["naming_patterns"]) >= 2


@pytest.mark.parametrize("project_type", ["houdini", "maya", "blender", "unreal"])
def test_init_creates_the_folders_of_each_ruleset(tmp_path: Path, project_type: str) -> None:
    rule = load_rule_file(bundled_rule_path(project_type))
    target = tmp_path / project_type

    result = CliRunner().invoke(main, ["init", "--type", project_type, "--path", str(target)])

    assert result.exit_code == 0
    for entry in rule["folder_template"]:
        assert (target / entry["path"]).is_dir()


def test_the_cli_offers_every_bundled_ruleset() -> None:
    data = Path(__file__).resolve().parents[1] / "pipeinit" / "data"

    assert sorted(PROJECT_TYPES) == sorted(p.stem for p in data.glob("*.yaml"))


def test_the_help_of_init_lists_the_dcc_types() -> None:
    result = CliRunner().invoke(main, ["init", "--help"])

    for name in ("houdini", "maya", "blender", "unreal"):
        assert name in result.output
