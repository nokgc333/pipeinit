# サンプルプロジェクトでの検証記録

> 実施日: 2026-10-28 / 環境: macOS(Apple Silicon)、Python 3.12、Houdini Indie 22.0.466(`hython`)
> 実行: `python examples/run_sample.py <出力フォルダ>`(Houdini・Maya・Unreal の制作を模したフォルダとファイルを作り、`init` → `validate` → `bump` を動かす)

## 何を確かめたか

- 3 種類の DCC のルールセット(Houdini・Maya・Unreal。ほかに Blender)で、制作の現場にありそうな名前を、正しく通し、間違いを検出できること
- 違反に、リネームの候補(`suggestion`)が付き、**ファイルは変更されない**こと
- `bump` が、既定ではドライランで、`--apply` で改名し、改名後に同じ名前では再実行できないこと(元のファイルが無いため)

## 実行ログ(パスは `<work>` と `<repo>` に置き換えた)

```text
==== houdini ====
$ pipeinit init --type houdini --path <work>/houdini_project --houdini-env
Created 6 folders, skipped 0 (already exist)
  created: hip
  created: geo
  created: render
  created: tex
  created: scripts
  created: assets/hda
Wrote Houdini environment snippet: <work>/houdini_project/.pipeinit/houdini.env
(exit code 0)

$ pipeinit validate <work>/houdini_project --rules <repo>/pipeinit/data/houdini.yaml
assets/hda/tornado.hda: 'tornado.hda' does not match: Houdini のシーン(例: SHOT010_fx_v003.hip); HDA(例: Studio_Tornado_v001.hda); キャッシュ・出力(例: SHOT010_fx_v003.bgeo.sc)
hip/SHOT020 lighting v001.hip: 'SHOT020 lighting v001.hip' does not match: Houdini のシーン(例: SHOT010_fx_v003.hip); HDA(例: Studio_Tornado_v001.hda); キャッシュ・出力(例: SHOT010_fx_v003.bgeo.sc)
  suggestion: SHOT020_lighting_v001.hip
hip/SHOT030_comp_v001.nk: 'SHOT030_comp_v001.nk' does not match: Houdini のシーン(例: SHOT010_fx_v003.hip); HDA(例: Studio_Tornado_v001.hda); キャッシュ・出力(例: SHOT010_fx_v003.bgeo.sc)
hip/shot020_fx_v3.hip: 'shot020_fx_v3.hip' does not match: Houdini のシーン(例: SHOT010_fx_v003.hip); HDA(例: Studio_Tornado_v001.hda); キャッシュ・出力(例: SHOT010_fx_v003.bgeo.sc)
  suggestion: SHOT020_fx_v003.hip
scripts/shelf.py: 'shelf.py' does not match: Houdini のシーン(例: SHOT010_fx_v003.hip); HDA(例: Studio_Tornado_v001.hda); キャッシュ・出力(例: SHOT010_fx_v003.bgeo.sc)
(exit code 1)

==== maya ====
$ pipeinit init --type maya --path <work>/maya_project
Created 7 folders, skipped 0 (already exist)
  created: scenes
  created: sourceimages
  created: images
  created: assets/characters
  created: assets/props
  created: cache
  created: scripts
(exit code 0)

$ pipeinit validate <work>/maya_project --rules <repo>/pipeinit/data/maya.yaml
assets/characters/hero final.ma: 'hero final.ma' does not match: Maya のショットシーン(例: SHOT010_anim_v003.ma); Maya のアセット(例: Character_Hero_v001.mb); テクスチャ(例: Hero_body_diffuse.png); 書き出し(例: Character_Hero.fbx)
(exit code 1)

==== unreal ====
$ pipeinit init --type unreal --path <work>/unreal_project
Created 7 folders, skipped 0 (already exist)
  created: Content/Characters
  created: Content/Environments
  created: Content/Props
  created: Content/Materials
  created: Content/Maps
  created: Content/Blueprints
  created: Source/Imports
(exit code 0)

$ pipeinit validate <work>/unreal_project --rules <repo>/pipeinit/data/unreal.yaml
Content/Maps/Forest.umap: 'Forest.umap' does not match: Unreal の推奨の接頭辞つきのアセット(例: SM_Chair_01.uasset、T_Wood_D.uasset); レベル(例: L_Forest_Main.umap); インポート元(例: Chair.fbx)
Content/Props/Chair_02.uasset: 'Chair_02.uasset' does not match: Unreal の推奨の接頭辞つきのアセット(例: SM_Chair_01.uasset、T_Wood_D.uasset); レベル(例: L_Forest_Main.umap); インポート元(例: Chair.fbx)
(exit code 1)

==== bump ====
$ pipeinit bump <work>/houdini_project/hip/SHOT010_fx_v002.hip
SHOT010_fx_v002.hip -> SHOT010_fx_v003.hip (dry-run, use --apply to rename)
(exit code 0)

$ pipeinit bump <work>/houdini_project/hip/SHOT010_fx_v002.hip --apply
SHOT010_fx_v002.hip -> SHOT010_fx_v003.hip
(exit code 0)

$ pipeinit bump <work>/houdini_project/hip/SHOT010_fx_v002.hip --apply
Usage: python -m pipeinit.cli bump [OPTIONS] FILENAME
Try 'python -m pipeinit.cli bump --help' for help.

Error: Invalid value for 'FILENAME': File '<work>/houdini_project/hip/SHOT010_fx_v002.hip' does not exist.
(exit code 2)

project: <work>
```

## 読み取れること

| 項目 | 結果 |
| --- | --- |
| Houdini | `.hip` / `.hda` / キャッシュの名前を検査。小文字の `shot020_fx_v3.hip` と、空白の `SHOT020 lighting v001.hip` を検出し、`SHOT020_fx_v003.hip` / `SHOT020_lighting_v001.hip` を提案した。Nuke のファイル(`.nk`)と `shelf.py` は、Houdini のルールの対象外として検出された(意図どおり) |
| Maya | `.ma` / `.mb` が、Maya のルールセットでは違反にならない(従来の Houdini 中心のルールでは違反だった)。`hero final.ma` だけが検出された |
| Unreal | 接頭辞(`SM_` `M_` `L_` など)のないアセットとレベル(`Chair_02.uasset`、`Forest.umap`)だけが検出された |
| bump | ドライラン → `--apply` → 同じファイル名での再実行は、元のファイルが無いため終了コード 2(使い方の誤り) |
| 終了コード | 違反あり = 1、違反なし・成功 = 0 |

## 見つかったこと(対処済み)

1. **生成した環境変数のスニペットが、命名の違反として検出された**: 初版は `houdini.env.snippet` をプロジェクト直下に書いていた。隠しフォルダ `.pipeinit/houdini.env` に移し、検査の対象外にした(テストで固定)。
2. **`$HIP` は、環境ファイルでは設定できない**: 実機の Houdini 22.0.466(`hython`)で確認した。`houdini.env` の `JOB` は反映されるが、`HIP` は Houdini が、カレントフォルダ・開いたシーンから決めるため、反映されない。スニペットは `JOB` だけにした。

## Houdini 実機での確認

`pipeinit init --type houdini --houdini-env` が書いた `.pipeinit/houdini.env` を、Houdini のユーザー設定フォルダ(`HOUDINI_USER_PREF_DIR=<dir>__HVER__`)に置いて `hython` を起動し、`hou.getenv("JOB")` を読んだ。

```text
JOB /…/hproj   (プロジェクトのルートが反映された)
HIP /…         (カレントフォルダ。環境ファイルの値は反映されない)
```

## Maya の曖昧さ

`Shot020_anim_v001.ma`(`Shot` が大文字小文字の混在)は、アセットの規則(`Character_Hero_v001.mb` の形)に合うため、違反にならない。ショットとアセットを名前の形だけで区別する限界で、区別が要る現場では、フォルダごとに別のルールファイルを `.pipeinit.yaml` で指定する。
