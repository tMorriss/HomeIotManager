# HomeIotManager 作業履歴 (Work History)

本ドキュメントは、HomeIotManager における改修案件・計画の履歴を記録するドキュメントです。

- **開発規約・計画書管理方針**: [../AGENTS.md](../AGENTS.md)
- **システム仕様書 (正式版)**: [architecture.md](architecture.md)
- **個別計画書一覧**: [plans/](plans/)

---

## 案件履歴一覧

| 計画日 | 案件名 | ステータス | 計画書 | 主な内容 |
|---|---|---|---|---|
| 2026-09-20 | in_out_log からの移行・再構築 | **中断 (Aborted)** | [plans/2026-09-20-migration-from-in-out-log.md](plans/2026-09-20-migration-from-in-out-log.md) | 現行 in_out_log の完全リプレイス。Podman Pod 化（Web: 8930, Worker: 10秒間隔）、パブリックリポジトリセキュリティ、MoneyBook 準拠 CI/CD。PR 1〜7 に細かく分割して実装。（PR 5 完了時点で非同期処理化計画へ移行） |
| 2026-09-21 | バッチ処理・Webサーバーの非同期処理化 (asyncio対応) | **完了 (Completed)** | [plans/2026-09-21-async-execution-plan.md](plans/2026-09-21-async-execution-plan.md) | Web サーバーおよび常駐バッチワーカー全般の `asyncio` 非同期化。`httpx`, `aiomysql`/`asyncmy`, ASGI 対応等によるリアルタイム性・レスポンス性能向上。PR Async 1〜6 に分割して実装。 |
| 2026-11-03 | Podman Quadlet への移行 | **完了 (Completed)** | [plans/2026-11-03-podman-quadlet-migration.md](plans/2026-11-03-podman-quadlet-migration.md) | PR #21をmainへマージ。`podman play kube` からQuadletへ移行し、Jenkins実行ユーザーのrootless Podman / systemdを使用、設定をPodman Secretsで注入。 |
| 2026-11-03 | in_out_log とのロジック差分修正 | **実装完了 (Implementation Completed)** | [plans/2026-11-03-restore-legacy-business-logic.md](plans/2026-11-03-restore-legacy-business-logic.md) | 移行後に生じた在宅・外出判定、ログ、Webhook、Hue・IFTTTの意図しない差分を、非同期構成を維持して修正。全78件とlint成功。tox unittestはWindows環境の`aiomysql`/`pwd`読み込み問題により実行不可。 |
| 2026-11-07 | Webhook 公開ポートを8082へ変更 | **実装中 (Implementation in Progress)** | [plans/2026-11-07-change-webhook-port-to-8082.md](plans/2026-11-07-change-webhook-port-to-8082.md) | Quadlet のホスト公開ポートと README・アーキテクチャ仕様を `8930` から `8082` に変更。デプロイ環境の Nginx 更新と疎通確認が残る。 |
| 2026-11-08 | SwitchBot 人感センサー Pro の Webhook 対応 | **実装中 (Implementation in Progress)** | [plans/2026-11-08-switchbot-presence-sensor-pro-webhook.md](plans/2026-11-08-switchbot-presence-sensor-pro-webhook.md) | Webhook をデバイス別に振り分け、Pro の `DETECTED` / `NOT_DETECTED` を `presence_sensor` テーブルへ保存。 |
| 2026-11-08 | Web エンドポイント整理 | **実装完了 (Implementation Completed)** | [plans/2026-11-08-web-endpoint-cleanup.md](plans/2026-11-08-web-endpoint-cleanup.md) | FastAPI 自動生成ドキュメントと未使用の /healthz を削除し、Web コンテナ内ポートを 8080 に統一。 |
