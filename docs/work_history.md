# HomeIotManager 作業履歴 (Work History)

本ドキュメントは、HomeIotManager における改修案件・計画の履歴を記録するドキュメントです。

- **開発規約・計画書管理方針**: [../AGENTS.md](../AGENTS.md)
- **システム仕様書 (正式版)**: [architecture.md](architecture.md)
- **個別計画書一覧**: [plans/](plans/)

---

## 案件履歴一覧

| 計画日 | 案件名 | ステータス | 計画書 | 主な内容 |
|---|---|---|---|---|
| 2026-09-20 | in_out_log からの移行・再構築 | **進行中 (Active)** | [plans/2026-09-20-migration-from-in-out-log.md](plans/2026-09-20-migration-from-in-out-log.md) | 現行 in_out_log の完全リプレイス。Podman Pod 化（Web: 8930, Worker: 10秒間隔）、パブリックリポジトリセキュリティ、MoneyBook 準拠 CI/CD。PR 1〜7 に細かく分割して実装。 |
| 2026-09-21 | バッチ処理・Webサーバーの非同期処理化 (asyncio対応) | **進行中 (Active)** | [plans/2026-09-21-async-execution-plan.md](plans/2026-09-21-async-execution-plan.md) | Web サーバーおよび常駐バッチワーカー全般の `asyncio` 非同期化。`httpx`, `aiomysql`/`asyncmy`, ASGI 対応等によるリアルタイム性・レスポンス性能向上。PR Async 1〜6 に分割して実装。 |
