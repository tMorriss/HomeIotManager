# HomeIotManager

HomeIotManager は、在宅・外出の自動判定、スマート家電（Philips Hue、ルンバ、シーリングライト）の自動制御、および入退室ログの記録を行う常駐型 IoT 連携システムです。

---

## 1. ディレクトリ構造

```
HomeIotManager/
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI 設定
├── homeiot/                     # メインアプリケーションパッケージ
│   └── __init__.py
├── requirements/                # 依存パッケージ定義
│   ├── requirements_dev.txt     # 開発環境用 (tox)
│   └── requirements_lint.txt    # リント・静的解析用 (flake8 等)
├── scripts/                     # 開発・運用サポートスクリプト
│   └── check_filenames.py       # スネークケースファイル名チェック
├── docs/                        # ドキュメント (architecture.md, work_history.md, plans/)
├── AGENTS.md                    # エージェント & 開発者向けガイド
├── tox.ini                      # tox 設定
├── .env.example                 # 環境変数サンプル
└── README.md                    # 本ドキュメント
```

---

## 2. 開発・テスト手順

本プロジェクトでは `tox` を使用してリントチェックを実行します。

### セットアップ

```bash
# 仮想環境の作成・有効化 (任意)
python3.12 -m venv .venv
source .venv/bin/activate

# 開発用依存関係 (tox) のインストール
pip install -r requirements/requirements_dev.txt
```

### リントの実行

```bash
# リント・静的解析 (flake8 & check_filenames.py) の実行
tox -e lint
```

---

## 3. ドキュメント

- [システム仕様書 (docs/architecture.md)](docs/architecture.md)
- [開発・運用ガイド (AGENTS.md)](AGENTS.md)
- [作業履歴一覧 (docs/work_history.md)](docs/work_history.md)
