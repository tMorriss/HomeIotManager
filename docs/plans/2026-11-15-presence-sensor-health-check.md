# Presence Sensor の死活監視計画

- **計画日**: 2026-11-15
- **対象**: SwitchBot Presence Sensor の死活状態記録と在室判定
- **ステータス**: 実装中

## 背景

Presence Sensor の最終イベントが `DETECTED` のままセンサーや SwitchBot 側に障害が起きると、古い値を使って在室状態が継続する。センサー死活を定期取得し、inactive が最後に確認されていたら Presence Sensor の値を在室判定から外す。

## 詳細設計

- `BatchWorker.start()` が周期処理一覧から在室判定（10秒）と死活監視（10分）を同列に起動し、停止要求までそれぞれを繰り返す。10分ごとに SwitchBot OpenAPI v1.1 の `GET /v1.1/devices/{deviceId}/status` を呼び出す。監視時刻は DB の `lasts` から計算しない。将来の周期処理も一覧へ追加する。
- `SwitchBotApiClient.request(method, path, ...)` を汎用 API 呼び出しとして用意し、パスの組み立ては呼び出し元で行う。`is_active(device_id)` からデバイス状態取得を呼び出す。API 認証は Open Token / Secret Key で署名し、`statusCode == 100` を active、それ以外と通信失敗を inactive とする。
- `lasts` に `presence_sensor_active` / `presence_sensor_inactive` を保存する。確認結果に対応するキーだけを UPSERT する。
- `presence_sensor_active` が `presence_sensor_inactive` より新しい場合だけ `presence_sensor` の最新状態を在室判定に使う。active が未記録の場合はセンサー値を使わない。
- `lasts.name` が20文字の環境では新しいキーを格納できないため、事前に `ALTER TABLE lasts MODIFY name VARCHAR(32) NOT NULL` を実行する。
- `SWITCHBOT_API_TOKEN`、`SWITCHBOT_API_SECRET`、`PRESENCE_SENSOR_DEVICE_ID` を Jenkins / Podman Secrets から Worker に注入する。

## DB 変更コマンド

死活監視を有効にする前に、既存の `lasts.name` カラムを拡張します。

```sql
ALTER TABLE lasts MODIFY name VARCHAR(32) NOT NULL;
```

## PR 分割計画

| PR | 内容 | 検証 |
|---|---|---|
| 1 | DB キー、`homeiot.clients.switchbot` の死活監視クライアント、Worker 定期処理、在室判定、設定・デプロイ・仕様書を一括更新 | `tox -e lint`、`tox -e unittest`、差分確認 |

## 進捗

- [x] 死活監視間隔と `lasts` キーを追加する。
- [x] SwitchBot OpenAPI 認証と状態取得を追加する。
- [x] Worker に10分間隔の監視を組み込む。
- [x] inactive 時に Presence Sensor の在室判定を無効化する。
- [x] 設定、Quadlet、Jenkins、README、アーキテクチャ仕様を更新する。
- [ ] デプロイ前に `lasts.name` を `VARCHAR(32)` へ拡張する。
- [x] `tox -e lint` を実行する。
- [ ] `tox -e unittest` を実行する（Windows 環境で `aiomysql` の import 時に `pwd` が見つからず collection で停止）。
