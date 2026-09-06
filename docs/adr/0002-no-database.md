# ADR-0002: DBを使わずYAMLを正本とする

## Status
Accepted (2026-09-07)

## Context
ルールデータは数KB〜数十KB規模のスタジオ設定であり、更新頻度も低い。

## Decision
SQLite等のDBを導入せず、YAMLファイル自体を正本とする。

## Consequences
良い: 依存を最小化でき、YAMLをGit管理するだけでルールの変更履歴が残る
悪い: 大規模なクエリ（横断検索等）が必要になった場合はDB導入を再検討する必要がある

## Alternatives Considered
- SQLite: 個人開発・小規模データ量のため、DB導入のオーバーヘッドがメリットを上回らないと判断
