"""実際の制作を模したサンプルプロジェクトで、init → validate → bump を動かす(記録用)。

使い方: `python examples/run_sample.py [出力フォルダ]`。出力は docs/sample-verification.md に記録している。
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

PIPEINIT = [sys.executable, "-m", "pipeinit.cli"]

HOUDINI_FILES = [
    "hip/SHOT010_fx_v001.hip",
    "hip/SHOT010_fx_v002.hip",
    "hip/shot020_fx_v3.hip",
    "hip/SHOT020 lighting v001.hip",
    "hip/SHOT030_comp_v001.nk",
    "geo/SHOT010_fx_v002.bgeo.sc",
    "geo/SHOT010_fx_v002.0001.exr",
    "assets/hda/Studio_Tornado_v001.hda",
    "assets/hda/tornado.hda",
    "scripts/shelf.py",
]
MAYA_FILES = [
    "scenes/SHOT010_anim_v004.ma",
    "scenes/SHOT010_anim_v005.mb",
    "scenes/Shot020_anim_v001.ma",
    "assets/characters/Character_Hero_v002.mb",
    "assets/characters/hero final.ma",
    "sourceimages/Hero_body_diffuse.png",
]
UNREAL_FILES = [
    "Content/Props/SM_Chair_01.uasset",
    "Content/Props/Chair_02.uasset",
    "Content/Materials/M_Wood.uasset",
    "Content/Maps/L_Forest_Main.umap",
    "Content/Maps/Forest.umap",
]


def run(*args: str, cwd: Path | None = None) -> None:
    print("$ pipeinit " + " ".join(args))
    result = subprocess.run(
        [*PIPEINIT, "--no-color", "--lang", "en", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        check=False,
    )
    print(result.stdout, end="")
    print(result.stderr, end="")
    print(f"(exit code {result.returncode})\n")


def populate(root: Path, files: list[str]) -> None:
    for name in files:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("sample\n")


def main() -> None:
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp())
    for project_type, files in (
        ("houdini", HOUDINI_FILES),
        ("maya", MAYA_FILES),
        ("unreal", UNREAL_FILES),
    ):
        root = base / f"{project_type}_project"
        print(f"==== {project_type} ====")
        extra = ["--houdini-env"] if project_type == "houdini" else []
        run("init", "--type", project_type, "--path", str(root), *extra)
        populate(root, files)
        run(
            "validate",
            str(root),
            "--rules",
            str(Path(__file__).parent.parent / "pipeinit" / "data" / f"{project_type}.yaml"),
        )
    houdini = base / "houdini_project"
    print("==== bump ====")
    run("bump", str(houdini / "hip" / "SHOT010_fx_v002.hip"))
    run("bump", str(houdini / "hip" / "SHOT010_fx_v002.hip"), "--apply")
    run("bump", str(houdini / "hip" / "SHOT010_fx_v002.hip"), "--apply")
    print("project:", base)


if __name__ == "__main__":
    main()
