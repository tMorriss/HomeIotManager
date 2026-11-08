# 在室確認への Presence Sensor 状態反映計画

- **起票日**: 2026-11-08
- **対象**: `presence_sensor` の最新状態を在室判定へ反映
- **ステータス**: 実装完了 (Implementation Completed)

---

## 1. 案件概要

### 背景

2026-11-08 の SwitchBot Presence Sensor Pro Webhook 対応で、センサーの `DETECTED` / `NOT_DETECTED` 状態を `presence_sensor` テーブルへ保存するようになった。一方、在室確認はスマートフォンへの Ping のみを参照している。

### 目的

`presence_sensor` の最新状態が `DETECTED` なら、スマートフォンが Ping に応答しなくても在宅として扱う。

---

## 2. 方針

1. `presence_sensor` の最新行を取得する DB メソッドを追加する。`datetime` 降順、同時刻の場合は `id` 降順とする。
2. `HomeService.is_present()` は既存の `WoPresence` 検知、Pro の最新 `DETECTED`、スマートフォン Ping のいずれかが在室を示せば `True` を返す。
3. 最新状態が `NOT_DETECTED` または履歴なしの場合、スマートフォン Ping の従来動作を維持する。
4. アーキテクチャ仕様書に在室判定の優先条件を記録する。

---

## 3. 実装・確認記録

- [x] 最新状態取得を DB アクセス層に追加する。
- [x] Presence Sensor Pro の最新 `DETECTED` を在室判定へ統合する。
- [x] 最新状態取得の DB 層テストと、スマホ Ping なしで在室になるサービス層テストを追加する。
- [x] アーキテクチャ仕様と作業履歴を更新する。
- [x] 変更差分を確認する。

テスト実行を試みましたが、Windows 環境の pytest で対象テストの開始後に処理が停止し、結果を取得できていません。
