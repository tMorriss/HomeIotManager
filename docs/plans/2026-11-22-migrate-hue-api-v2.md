# Hue API v2 への移行計画

## 背景

Hue ブリッジの旧 `/api` API から HTTPS の `/clip/v2` API へ移行する。API キーは `hue-application-key` ヘッダーで送信し、CA バンドルでブリッジ証明書を検証する。DNS は利用できないため、ブリッジ ID を TLS / HTTP のホスト名として使いつつ、接続先 IP アドレスを固定する。

## 設計

- `HUE_BRIDGE_ID` と `HUE_APPLICATION_KEY` を環境変数で受け取り、必須設定にする。
- `HUE_BRIDGE_IP` へ直接接続し、`HUE_BRIDGE_ID` を Host ヘッダーと TLS SNI に使う。CA は `ca/huebridge_cacert_bundle.pem` を検証に使う。
- `/clip/v2/resource/scene` と `/clip/v2/resource/grouped_light` を使う。
- `HUE_ON_SCENE_RESOURCE_ID`、`HUE_ON_GROUPED_LIGHT_RESOURCE_ID`、`HUE_OFF_GROUPED_LIGHT_RESOURCE_ID` に v2 リソース UUID を設定し、変換やリソース一覧検索を行わず直接指定する。
- シーンは `recall.action=active` で呼び出し、グループ消灯と状態取得は grouped_light を利用する。
- `.env.example`、Jenkins / Quadlet の環境変数配線、アーキテクチャ仕様を更新する。

## 作業チェックリスト

- [x] `codex/hue-api-v2` ブランチを作成
- [x] Hue v2 通信、TLS / IP 解決、認証ヘッダーを実装
- [x] 設定・デプロイ・サンプル環境変数を更新
- [x] アーキテクチャ仕様と作業履歴を更新
- [x] 変更内容を確認

## 検証手順

- `tox -e lint`
- `tox -e unittest`
- 実機では Web / Worker の両方から Hue ブリッジへの TLS 接続、シーン呼び出し、状態取得、消灯を確認する。
