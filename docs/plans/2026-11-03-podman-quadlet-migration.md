# Podman Quadlet 移行計画

- **起票日**: 2026-11-03
- **対象**: HomeIotManager の Podman 起動・デプロイ構成
- **ステータス**: 実装完了・PRレビュー待ち（PR #21）

---

## 1. 案件概要

### 背景

現行デプロイは `build/pod.yaml` を `podman play kube` に渡してWebとWorkerを起動している。systemdによるコンテナ管理がなく、Jenkinsスクリプトが `PODMAN_USER` を介してPodmanを実行していた。

### 目的

PodとWeb / WorkerコンテナをPodman Quadletで定義し、実行ユーザーのrootless Podmanとユーザーsystemdで管理する。Jenkinsの実行ユーザーをPodmanユーザーとして扱い、`PODMAN_USER` によるユーザー切り替えをなくす。

---

## 2. 方針

1. `build/quadlet/` にPod、Web、WorkerのQuadletテンプレートを追加する。
2. ホストの `8930` からコンテナ内 `8001` へのポート転送を維持する。
3. Jenkinsスクリプトから `podman play kube` と `PODMAN_USER` 依存を取り除き、実行ユーザーのPodman、ユーザーsystemd、`$HOME`、`XDG_RUNTIME_DIR` を使う。
4. アプリケーション設定はPodman Secretsとして登録し、両コンテナの環境変数として渡す。
5. Jenkinsスクリプトから `loginctl enable-linger` は実行しない。ホスト起動時の自動起動が必要な環境では、管理者が実行ユーザーのlingerを事前に設定する。
6. README、アーキテクチャ仕様、AGENTS.mdを新しい構成に合わせる。

---

## 3. 受け入れ条件

- [x] QuadletのPod / Web / Worker定義が追加されている。
- [x] Jenkinsスクリプトが実行ユーザーのrootless Podmanとユーザーsystemdを使う。
- [x] `PODMAN_USER`、`podman play kube`、自動linger設定が現行デプロイ処理から除去されている。
- [x] アプリケーション設定をPodman Secrets経由でコンテナに渡す。
- [x] READMEとアーキテクチャ仕様が新構成を説明している。
- [ ] LinuxホストでQuadlet生成・Pod起動・WebとWorkerの稼働を確認する。
- [ ] `tox -e lint` と `tox -e unittest` を実行する。

---

## 4. 実装・確認記録

- 実装はPR #21（`codex/homeiot-quadlet-migration`）に含めた。
- `git diff --check` は通過。
- Linux上のPodman / systemd実機確認とtoxの実行は未実施。
