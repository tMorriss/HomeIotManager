'''HomeIotManager - CLI エントリーポイント モジュール

`python -m homeiot.cli` 経由で web（FastAPI サーバー）および worker（常駐バッチワーカー）の起動を行います。
'''

import argparse
import asyncio
import sys
from typing import Optional, Sequence

import uvicorn

from homeiot import constants
from homeiot.services.batch_worker import BatchWorker


def main(argv: Optional[Sequence[str]] = None) -> None:
    '''CLI のメインエントリーポイント関数。'''
    parser = argparse.ArgumentParser(
        prog='homeiot',
        description='HomeIotManager CLI - web server or batch worker',
    )
    subparsers = parser.add_subparsers(dest='subcommand', required=True)

    # worker サブコマンド
    subparsers.add_parser('worker', help='Start resident batch worker')

    # web サブコマンド
    web_parser = subparsers.add_parser('web', help='Start FastAPI web server')
    web_parser.add_argument(
        '--host', default='0.0.0.0', help='Bind host (default: 0.0.0.0)'
    )
    web_parser.add_argument(
        '--port',
        type=int,
        default=constants.WEB_PORT,
        help=f'Bind port (default: {constants.WEB_PORT})',
    )

    args = parser.parse_args(argv)

    if args.subcommand == 'worker':
        worker = BatchWorker()
        asyncio.run(worker.start())
    elif args.subcommand == 'web':
        uvicorn.run(
            'homeiot.app:create_app',
            factory=True,
            host=args.host,
            port=args.port,
        )


if __name__ == '__main__':
    main(sys.argv[1:])
