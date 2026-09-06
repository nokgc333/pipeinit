# PipeInit

CG/ゲームパイプライン向けの、プロジェクトフォルダ自動生成・命名規則バリデーション・バージョン採番CLIツール。

## 目的・背景

プロジェクト立ち上げ時のフォルダ構成バラつきと、`SHOT010_lighting_v003.hip` のような命名規則違反・バージョン番号の重複／飛びは、現場で最初に問題化する「地味だが全員が困る」領域です。PipeInitはこれをYAML駆動のルールエンジンで自動化・標準化します。

詳細な要件定義・設計判断は [docs/要件定義書_v2.md](docs/要件定義書_v2.md) / [docs/仕様書_v2.md](docs/仕様書_v2.md) を参照してください。

## 技術スタック

- Python 3.11+
- [Click](https://click.palletsprojects.com/) 8.x（CLIフレームワーク）
- [PyYAML](https://pyyaml.org/) 6.x（`yaml.safe_load`のみ使用、任意コード実行を防止）
- pytest / pytest-cov / mypy(strict) / black / isort / flake8 / pip-audit

## インストール

```bash
git clone <this-repo>
cd pipeinit
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## 使用方法

```bash
# プロジェクト種別に応じたフォルダツリーを生成
pipeinit init --type game --path ./my-project

# 命名規則違反を検出（exit code 0=違反なし / 1=違反あり）
pipeinit validate ./my-project/shots
pipeinit validate ./my-project/shots --format json

# バージョン番号のインクリメント（既定はドライラン、--applyで実際にリネーム）
pipeinit bump SHOT010_lighting_v003.hip
pipeinit bump SHOT010_lighting_v003.hip --apply
```

`--type` は `game` / `film` / `generic` から選択します。各種別ごとのルールは [`rules/`](rules/) 配下のYAMLで定義されており、スタジオごとに規則を差し替える場合はこのYAMLを編集するだけで済みます（コード変更不要）。

## テスト

```bash
pytest --cov=pipeinit --cov-report=term-missing
black --check . && isort --check . && flake8 pipeinit/ tests/ && mypy pipeinit/
```

## 既知の制限事項

- Windows環境は簡易対応のみ（`pathlib.Path`によるパス区切り吸収のみで、CI上でのWindows検証は行っていない）
- ファイル数1万件規模での性能は保証対象外（3,000〜10,000件規模での実測は今後の課題）
- `folder_template`は同一ルールファイル内で完結し、ShotGrid等の外部システムとの同期機能は持たない

## Design Decisions

- **正規表現+YAML方式を採用し、専用パーサー/DSLは自作していない** — 命名規則は文字列パターンの集合であり構文木を要しないため（[ADR-0001](docs/adr/0001-regex-and-yaml.md)）
- **DBを使わずYAMLを正本とする** — 小規模データ量に対してDB導入のオーバーヘッドが見合わないため（[ADR-0002](docs/adr/0002-no-database.md)）
- **`bump`は既定でドライラン、`--apply`で明示的にオプトイン** — ファイルシステムを変更する操作は誤操作時の被害が大きいため、fail-safeな既定動作を優先した（[ADR-0003](docs/adr/0003-dry-run-by-default.md)）
- **YAML読込は`yaml.safe_load`のみ使用** — `yaml.load`はタグ経由で任意のPythonオブジェクトを構築できてしまうため、多層防御として`safe_load`に固定した

## ライセンス

MIT License（[LICENSE](LICENSE)参照）
