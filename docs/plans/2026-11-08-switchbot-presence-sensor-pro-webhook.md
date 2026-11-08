# SwitchBot 人感センサー Pro の Webhook 対応計画

- **起票日**: 2026-11-08
- **対象**: SwitchBot Webhook のデバイス追加と検知状態の記録
- **ステータス**: 実装中 (Implementation in Progress)

---

## 1. 案件概要

### 背景

現在の `POST /switchbot/all` は、`WoPresence` の `DETECTED` を前提に解析し、在宅判定処理へ直接つないでいる。人感センサー Pro は `deviceType: Presence Sensor` と `DETECTED` / `NOT_DETECTED` を送信するため、現状の実装では検知状態を扱えない。

### 目的

Pro の検知状態を専用の MySQL テーブルへ履歴として保存する。テーブルは `in_out` と同じ `id`、`datetime`、`value` の構成とし、`value` は `NOT_DETECTED=0`、`DETECTED=1` とする。デバイス別の処理を共通のWebhook受信・検証から切り離し、新しい SwitchBot デバイスを追加しやすくする。

---

## 2. 方針

1. Webhook ペイロードの共通検証とデバイス別処理を分離する。
2. 既存 `WoPresence` の `DETECTED` は、これまで通りスマホ未在宅時の帰宅処理へつなぐ。
3. `Presence Sensor` は `DETECTED` と `NOT_DETECTED` の両方を `presence_sensor` テーブルへ記録する。
4. 新テーブルは `in_out` と同じ列構成 (`id INT AUTO_INCREMENT PK`, `datetime DATETIME`, `value TINYINT(1)`) とする。SwitchBot の `timeOfSample` を記録時刻に使い、欠落時は受信時刻を使う。
5. SQL はプレースホルダで値を渡す。DB スキーマの作成はアプリケーション起動時に行わず、デプロイ時の手動DDLとして案内する。
6. 対応外のデバイス種別・状態は既存互換性を保って受理し、状態変更や在宅処理は行わない。

---

## 3. PR 分割

| PR | 内容 | 検証 |
|---|---|---|
| 1 | SwitchBot Webhook のデバイス別ディスパッチ、Pro 用DB保存、関連テスト、DDL・仕様書更新 | `tox -e lint`、`tox -e unittest`、差分確認 |

---

## 4. 受け入れ条件

- [ ] 人感センサー Pro の `DETECTED` と `NOT_DETECTED` が `presence_sensor` にそれぞれ `1` / `0` として保存される。
- [ ] `timeOfSample` を `datetime` として保存し、未指定時は受信時刻を使う。
- [ ] 既存 `WoPresence` の帰宅処理とトークン検証の振る舞いを維持する。
- [ ] Webhook 共通処理とデバイス別処理が分離され、新しいデバイスのハンドラーを追加できる。
- [ ] アーキテクチャ仕様に新テーブル、Webhook の振り分け、DDL を記載する。
- [ ] lint と unit test が成功する。

---

## 5. 実装・確認記録

- 実装ブランチ: 作業中
- デプロイ環境でのテーブル作成および実Webhook受信確認は未実施。
- `tox -e lint` は成功。
- `tox -e unittest` は Windows 環境で `aiomysql` が POSIX 専用の `pwd` を import するため、テスト収集時に失敗。Webhook時刻変換の追加テスト2件は個別実行で成功。
