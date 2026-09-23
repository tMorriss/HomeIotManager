'''HomeIotManager - CLI エントリーポイント モジュール

`python -m homeiot.cli web` や `python -m homeiot.cli worker` でサービス群を起動します。
'''

import argparse
import asyncio
import logging

import uvicorn

from homeiot.app import create_app
from homeiot.config import Config
from homeiot.services.batch_worker import BatchWorker

logger = logging.getLogger(__name__)


def run_web(args: argparse.Namespace) -> None:
    '''FastAPI Web サーバーを Uvicorn 経由で起動します。'''
    config = Config()
    app = create_app(config=config)
    uvicorn.run(app, host=args.host, port=args.port)


def run_worker(args: argparse.Namespace) -> None:
    '''常駐非同期バッチワーカーを起動します。'''
    worker = BatchWorker()
    asyncio.run(worker.run())


def main() -> None:
    '''CLI メイン関数'''
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    )

    parser = argparse.ArgumentParser(description='HomeIotManager CLI')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # web サブコマンド
    web_parser = subparsers.add_parser('web', help='Run FastAPI web server')
    web_parser.add_argument('--host', type=str, default='0.0.0.0', help='Host address to bind')
    web_parser.add_argument('--port', type=int, default=8930, help='Port to bind')
    web_parser.set_defaults(func=run_web)

    # worker サブコマンド
    worker_parser = subparsers.add_parser('worker', help='Run batch worker')
    worker_parser.set_defaults(func=run_worker)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
