# Changelog

形式は [Keep a Changelog](https://keepachangelog.com/) に、版の付け方は [Semantic Versioning](https://semver.org/) に従う。

## [0.2.0] - 2026-10-28

### Added

- Houdini・Maya・Blender・Unreal のルールセット(`--type houdini|maya|blender|unreal`)
- 設定ファイル `.pipeinit.yaml`(カレントから親へ自動検出)と、ユーザー設定(`rules` / `lang` / `project_type`)
- 違反したファイル名への、リネーム候補(`suggestion`。ファイルは変更しない)
- `init --houdini-env`: Houdini の `$JOB` を設定するスニペット
- pre-commit のフック(`pipeinit-validate`)。`validate` は、複数のファイル・フォルダを受け取る
- `--json`(`init` / `validate` / `bump`)、`--quiet` / `--verbose` / `--no-color`、`--lang ja|en`、`pipeinit completion bash|zsh|fish`、`--help` の終了コード表

### Changed

- ルールファイルの検証を強化(どのファイルのどの項目か、正規表現の誤り、絶対パスなどを、原因つきのエラーに)
- 同梱のルールをパッケージの中(`pipeinit/data/`)に移し、インストール後も動くように
- `validate` は、ファイルを 1 つずつ走査し、シンボリックリンクのフォルダを辿らない
- CLI を、`commands` / `presenter` / `messages` / `exit_codes` に分割

### Fixed

- `bump --apply` が、リネーム先に同名のファイルが現れたとき、上書きしてしまう可能性があった(原子的に失敗するように)
- 書き込み権限のないフォルダで、トレースバックが出ていた(終了コード 5 とメッセージ)

## [0.1.0]

- 最初の版: `init` / `validate` / `bump`
