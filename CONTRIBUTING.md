# Contributing

## 開発の準備

```bash
git clone https://github.com/nokgc333/pipeinit.git && cd pipeinit
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install          # 任意(black・isort・flake8・gitleaks)
```

## 変更の流れ

1. `main` から、作業ブランチを切る(`feat/` `fix/` `refactor/` `test/` `docs/` `chore/` + ケバブケース)
2. **テストを先に書く**(RED → GREEN → REFACTOR)。新機能・バグ修正には、必ずテストを付ける
3. 次をすべて通す(CI と同じ)

   ```bash
   black --check . && isort --check . && flake8 pipeinit tests examples && mypy pipeinit
   pytest --cov-fail-under=95
   ```

4. コミットは、[Conventional Commits](https://www.conventionalcommits.org/) の形式で、説明は英語・小文字の命令形・末尾にピリオドなし(例: `feat: add a blender ruleset`)
5. `main` へは、PR で取り込む(CI が通ってから、マージコミットで)

## ルールセットを足す

1. `pipeinit/data/<名前>.yaml` を作る(`schema_version: 1`、`folder_template`、`naming_patterns`)
2. `pipeinit/cli.py` の `PROJECT_TYPES` に名前を足す(テストが、同梱のルールと選択肢の一致を確かめる)
3. `tests/test_rulesets.py` に、通る名前・通らない名前を足す

## 方針

- ファイルを変更する操作は、既定で何もしない(ドライラン)か、既存を上書きしない
- ルールの YAML は `yaml.safe_load` だけで読み、値はスキーマで検証する
- 出力は `presenter`、メッセージは `messages`(日本語と英語の両方)、終了コードは `exit_codes` に置く。`cli.py` には、コマンドの定義だけを書く
- Windows でも動く(パスは `pathlib`、ファイルの読み書きは `encoding="utf-8"` を明示する)

## 脆弱性の報告

公開の Issue に書かず、リポジトリの Security のページから、非公開で報告してほしい。
