# HomeIotManager システム仕様書 (Architecture & System Specification)

本ドキュメントは、HomeIotManager のシステムアーキテクチャ、コンテナ設計、各コンポーネントの責務、データベース設計、および外部連携仕様を定義する正式版ドキュメントです。

---

## 1. システム概要

**HomeIotManager** は、在宅・外出の自動判定、スマート家電（Philips Hue、ルンバ、シーリングライト）の自動制御、および入退室履歴ログの保存を行う常駐型 IoT 連携管理システムです。

### 主な役割
- **在宅 / 外出の検知**:
  - スマートフォンの ICMP Ping 応答（宅内 Wi-Fi 接続状態）の定期監視
  - SwitchBot 人感センサー（`WoPresence`）からの Webhook イベント受信
- **スマート家電の自動制御**:
  - 帰宅時: 時間帯に応じた照明（Philips Hue、シーリングライト）の自動点灯、ルンバの自動帰還（Dock）
  - 外出時: 一定時間経過後の自動消灯、日中時間帯かつ未清掃時のルンバ自動清掃開始
- **設定・状態管理**:
  - ルンバ稼働抑制日（一時的な清掃停止日）のデータベース管理および制御ロジック（※保守コスト削減のため Web UI 設定画面は非搭載）
  - MySQL による状態日時（`lasts`）、抑制日（`roomy_lock`）、入退室ログ（`in_out`）の永続化

---

## 2. 全体アーキテクチャ

```mermaid
flowchart TD
    subgraph Host["ホストマシン (Linux / Podman)"]
        Nginx["ホスト Nginx / リバースプロキシ\n(HTTPS: tmorriss.com)"]
        
        subgraph Pod["Podman Quadlet Pod: homeiot-pod"]
            direction TB
            WebContainer["Web コンテナ\n(FastAPI)\nListen: 0.0.0.0:8001"]
            WorkerContainer["Worker コンテナ\n(常駐バッチループ)\n10秒間隔で監視"]
        end

        MySQL[(既存 MySQL サーバー\nin_out / lasts / roomy_lock)]
    end

    subgraph LAN["宅内ローカルネットワーク"]
        Smartphones["スマートフォン\n(ICMP Ping 応答)"]
        HueBridge["Philips Hue ブリッジ\n(ローカル REST API)"]
    end

    subgraph External["外部クラウド / API"]
        SwitchBotCloud["SwitchBot Cloud\n(人感センサー Webhook 送信)"]
        IFTTT["IFTTT Maker Webhook\n(ルンバ / シーリングライト)"]
    end

    %% 通信フロー
    SwitchBotCloud -->|"POST /switchbot/all"| Nginx
    Nginx -->|"Proxy: http://127.0.0.1:8930"| WebContainer
    WebContainer -->|"在宅検知時\n家電制御 & DB記録"| HueBridge
    WebContainer -->|"在宅検知時"| IFTTT
    WebContainer --> MySQL

    WorkerContainer -->|"ICMP Ping"| Smartphones
    WorkerContainer -->|"外出/帰宅検知時\n家電制御"| HueBridge
    WorkerContainer -->|"外出/帰宅検知時"| IFTTT
    WorkerContainer --> MySQL
```

---

## 3. コンテナ設計 (Podman Quadlet)

MoneyBook と同様に、Quadlet の `.pod` と `.container` ユニット（`build/quadlet/`）で1つの Pod `homeiot-pod` と2つのコンテナを管理します。Jenkins ジョブはPodmanを運用するLinuxユーザー自身として実行し、そのユーザーのrootless Podman・ユーザーsystemdを使用します。ユニットは実行ユーザーの `$HOME/.config/containers/systemd/homeiot/` に配置します。Pod のポート転送はホスト `8930` からコンテナ `8001` です。

- **タイムゾーン**: Docker イメージに `tzdata` を含め、`TZ=Asia/Tokyo` と `/etc/localtime` を設定します。Web / Worker の `datetime.now()` および `DATETIME` 保存値は日本時間を基準にします。

- **Web コンテナ (`homeiot-web`)**:
  - Uvicorn + FastAPI
  - コンテナ内ポート **8001** でリッスン（ホスト側では **8930** で公開）
  - エンドポイント:
    - `POST /switchbot/all`: SwitchBot 人感センサー（`WoPresence`）の検知 Webhook 受信（トークン検証付き）
    - `GET /healthz`: ヘルスチェック用エンドポイント
  ※ 保守コスト削減のため、ルンバ稼働抑制日（`roomy_lock`）の Web UI 設定画面（`/settings`）は非搭載とし、DB テーブルおよびバックエンド判定ロジックのみを保持します。
- **Worker コンテナ (`homeiot-worker`)**:
  - 常駐 Python プロセス
  - 10秒間隔（定数 `CHECK_INTERVAL_SECONDS`）で在宅監視ループを実行
  - スマホへの Ping 疎通確認、在宅・外出の判定、ルンバ・照明の自動制御、DB 記録
- **LAN 接続**:
  - Worker は Podman の rootless ネットワークから宅内スマートフォンへ ICMP Ping を送り、Hue ブリッジへ接続します。Pod のホストポート公開は Web への受信接続に使用します。

---

## 4. データベース仕様 (MySQL)

既存の MySQL データベースおよびテーブルをそのまま利用します。
SQL クエリ発行時はプリペアドステートメント（パラメータバインド）を用い、SQL インジェクション対策を徹底します。

### テーブル定義

#### 1. `lasts` テーブル
各種イベントの最終日時を保持します。テーブルが空、または対象キーが未登録の場合、アプリケーションの取得結果は `None` です。

| カラム名 | 型 | 説明 |
|---|---|---|
| `name` | `VARCHAR(20) NOT NULL` (PK) | イベント種別キー (`in`, `out`, `roomy`, `hue_off`) |
| `time` | `DATETIME NOT NULL` | 最終記録日時 |

実環境の定義は `name` が PRIMARY KEY です。保存には `INSERT ... ON DUPLICATE KEY UPDATE` を使い、キーが未登録なら INSERT、登録済みなら `time` を UPDATE します。この処理は1文で原子的に実行されます。

- `in`: 最終在宅検知時刻
- `out`: 最終帰宅処理時刻（帰宅判定時に更新。外出確定時には更新しない）
- `roomy`: 最終ルンバ稼働日/時刻
- `hue_off`: 最終 Hue 消灯時刻

#### 2. `roomy_lock` テーブル
ルンバの稼働を抑制する日付を保持します。抑制日が当日以降の場合はルンバを自動起動しません。テーブルが空の場合、抑制日はありません。

| カラム名 | 型 | 説明 |
|---|---|---|
| `date` | `DATE NOT NULL` | ルンバ稼働抑制指定日 |

実環境では `date` に PRIMARY KEY / UNIQUE 制約がありません。そのため `set_roomy_lock()` は呼び出すたびに行を追加し、`get_roomy_lock()` はその中で最も新しい日付を取得します。`delete_roomy_lock()` は全行を削除します。

#### 3. `in_out` テーブル
在宅・外出イベントの履歴ログテーブルです。`datetime` と `value` は必須です。

| カラム名 | 型 | 説明 |
|---|---|---|
| `id` | `INT(11) NOT NULL` (PK, AUTO_INCREMENT) | 行 ID |
| `datetime` | `DATETIME NOT NULL` | イベント発生日時 |
| `value` | `TINYINT(1) NOT NULL` | イベント種別 (`0`: 外出, `1`: 帰宅) |

アプリケーションは `id` を指定せずに INSERT し、DB の AUTO_INCREMENT に採番させます。入退室ログ追加処理は `datetime` と `value` の両方に値を渡します。

### 入退室判定とログ記録

- Worker は10秒間隔で判定します。スマートフォンのいずれかに Ping 応答があれば在宅、人感センサーの有効な `DETECTED` イベントも在宅検知として扱います。
- 在宅検知時、`lasts.in` から5分以上経過していれば帰宅と判定します。このとき `in_out` に外出 (`value=0`, 前回 `lasts.in` の時刻) と帰宅 (`value=1`, 現在時刻) を順に記録し、`lasts.in` / `lasts.out` を現在時刻に更新します。
- 不在時は、`lasts.in` から5分以上経過して外出後の制御対象になります。外出確定時点では `in_out` に行を追加しません。
- `lasts.out` から3分以内の不在は帰宅直後の猶予として `lasts.in` を延長します。`lasts.out` が未登録の場合は帰宅直後である根拠がないため、この猶予を適用しません。
- `lasts` の各更新と `in_out` の複数 INSERT は、現状では単一トランザクションにまとめていません。DBエラー時には一部だけ保存される可能性があります。
- Worker は前回の判定完了を待たず10秒ごとに次の判定を開始し、Webhook も別プロセスから同じ状態を更新します。両者が同時に帰宅判定すると重複処理になる可能性があります。

---

## 5. 外部連携クライアント仕様

各外部インターフェースとの通信層は、独立したクライアントモジュールとして疎結合に実装します。

1. **ICMP Ping クライアント (`homeiot.clients.ping`)**:
   - `TARGET_PHONE_IPS` に定義された各スマホ IP に対して `ping -c 1 -w 1 <ip>` を実行。
   - 1台でも疎通成功（終了コード 0）すれば「スマホ在宅」と判定。
2. **Philips Hue クライアント (`homeiot.clients.hue`)**:
   - Hue ブリッジのローカル REST API 経由で通信。
   - 点灯: 指定グループに対して指定シーンを呼び出し (`PUT /api/<user>/groups/<id>/action`)
   - 消灯: 指定グループを消灯 (`PUT /api/<user>/groups/<id>/action`)
   - 状態取得: グループの現在の点灯状態を取得 (`GET /api/<user>/groups/<id>`)
3. **IFTTT クライアント (`homeiot.clients.ifttt`)**:
   - IFTTT Webhook を介して以下のイベントをトリガー：
     - `start_roomy`: ルンバの清掃開始
     - `dock_roomy`: ルンバの帰還
     - `turn_on_ceiling_light`: シーリングライト点灯
     - `turn_off_ceiling_light`: シーリングライト消灯
4. **SwitchBot クライアント / ハンドラー (`homeiot.clients.switchbot`, `homeiot.web.webhook`)**:
   - SwitchBot Cloud からの Webhook ペイロード（`changeReport`, `WoPresence`, `DETECTED`）を検証・解析。
   - トークン検証に合格し、かつスマホ未在宅の状態で人感センサーが検知した場合に「帰宅」処理を即時トリガー。

---

## 6. 設定・環境変数管理方針

本プロジェクトは **GitHub パブリックリポジトリ** であるため、設定は以下の2種類に厳格に分離して管理します。

### 6.1 機密情報・インフラ環境変数 (Jenkins 管理)
リポジトリ内には一切ハードコードせず、Jenkins の Credentials / パラメータからコンテナ起動時に注入します。

| 環境変数名 | 必須 | 説明 |
|---|---|---|
| `DB_HOST` | **必須** | MySQL サーバーホスト |
| `DB_PORT` | **必須** | MySQL 接続ポート (例: `3306`) |
| `DB_USER` | **必須** | MySQL 接続ユーザー名 |
| `DB_PASS` | **必須** | MySQL 接続パスワード |
| `DB_NAME` | **必須** | データベース名 |
| `TARGET_PHONE_IPS` | **必須** | 在宅判定対象スマホのIPアドレス（カンマ区切り。例: `<phone-ip-1>,<phone-ip-2>`） |
| `HUE_BRIDGE_IP` | **必須** | Philips Hue ブリッジの IP アドレス |
| `HUE_API_USER` | **必須** | Philips Hue の API ユーザーキー（ハッシュ文字列） |
| `HUE_ON_SCENE_ID` | **必須** | 帰宅時に呼び出すシーン ID |
| `IFTTT_WEBHOOK_KEY` | **必須** | IFTTT Webhook サービスの秘密キー |
| `SWITCHBOT_WEBHOOK_TOKEN` | **必須** | SwitchBot Webhook リクエスト検証用トークン |

### 6.2 動作パラメータ・数値設定 (`homeiot/constants.py` に集約)
環境変数化する必要のない動作パラメータは、変更時に直接コードを編集できるよう `homeiot/constants.py` の1箇所にまとめて定義します。

| 定数名 | 設定値 | 説明 |
|---|---|---|
| `CHECK_INTERVAL_SECONDS` | `10` | Worker 常駐プロセスの監視インターバル（10秒） |
| `OUT_THRESHOLD_SECONDS` | `300` | 外出・帰宅確定までのしきい値（5分 / 300秒） |
| `HUE_THRESHOLD_SECONDS` | `600` | ライト消灯判定のしきい値（10分 / 600秒） |
| `LAST_IN_THRESHOLD_SECONDS` | `180` | 帰宅直後の在宅維持判定しきい値（3分 / 180秒） |
| `HUE_ON_BEGIN_HOUR` | `17` | 自動点灯を開始する時刻（17時） |
| `HUE_ON_END_HOUR` | `6` | 自動点灯を終了する時刻（6時） |
| `ROOMY_SLEEP_START_HOUR` | `22` | ルンバ稼働を禁止する夜間開始時刻（22時） |
| `ROOMY_SLEEP_END_HOUR` | `6` | ルンバ稼働を禁止する早朝終了時刻（6時） |
| `HUE_ON_GROUP_ID` | `'2'` | 帰宅時点灯対象の Hue グループ ID |
| `HUE_OFF_GROUP_ID` | `'3'` | 外出時消灯対象の Hue グループ ID |
| `WEB_PORT` | `8001` | Web コンテナ内のリッスンポート（ホスト側は `8930`） |

---

## 7. デプロイメント設計 (MoneyBook 準拠)

MoneyBook の Quadlet 方式に準拠し、Jenkins パイプラインから `build/jenkins.sh` を実行してデプロイします。Jenkins ジョブの実行ユーザーがPodman・systemdの実行ユーザーになります。全てのアプリケーション設定値は Podman Secrets に登録し、Web / Worker コンテナの環境変数として注入します。ユニットは実行ユーザーの `$HOME/.config/containers/systemd/homeiot/` に配置されます。

```mermaid
sequenceDiagram
    autonumber
    participant Jenkins as Jenkins
    participant Host as ホスト (Podman)
    participant Systemd as ユーザー systemd / Quadlet
    participant Pod as homeiot-pod

    Jenkins->>Jenkins: [skip ci] コミットチェック
    Jenkins->>Jenkins: 必須環境変数のバリデーション
    Jenkins->>Jenkins: ランダムな BUILD_TAG 生成
    Jenkins->>Host: ベースイメージ (python:3.12-slim) pull
    Jenkins->>Host: podman build (localhost/homeiot:BUILD_TAG)
    Jenkins->>Host: 既存 Pod の停止・削除
    Jenkins->>Host: 設定値を Podman Secrets に登録
    Jenkins->>Systemd: Quadlet ユニット配置・daemon-reload・再起動
    Systemd->>Pod: homeiot-pod.service 起動
    Jenkins->>Host: 旧タグイメージのクリーンアップ
```

---

## 8. コード品質 & CI/CD 方針

- **言語・ランタイム**: Python 3.12
- **リンター**: `flake8`（シングルクオート強制、最大行長 140、インポート順序チェック、ファイル名規約チェック）
- **単体テスト**: `unittest` + `coverage.py`（目標カバレッジ 90% 以上、コアロジック 100%）
- **テスト自動化**: `tox` によるローカル検証（`tox -e lint`, `tox -e unittest`）
- **CI**: GitHub Actions（`.github/workflows/ci.yml`）による PR / Push 時の自動テスト
