'''HomeIotManager - CLI エントリポイント モジュール

`python -m homeiot.cli web` または `python -m homeiot.cli worker` で
Web サーバー / 常駐バッチワーカーを起動するための CLI コマンドを提供します。
'''

import argparse
import sys

from homeiot import constants
from homeiot.app import create_app
from homeiot.services.batch_worker import run_worker


def main() -> None:
    '''CLI メイン関数'''
    parser = argparse.ArgumentParser(description='HomeIotManager CLI')
    subparsers = parser.add_subparsers(dest='command', help='Subcommands')

    subparsers.add_parser('web', help='Start Web server (Flask)')
    subparsers.add_parser('worker', help='Start resident batch worker')

    args = parser.parse_args()

    if args.command == 'web':
        app = create_app()
        app.run(host='0.0.0.0', port=constants.WEB_PORT)
    elif args.command == 'worker':
        run_worker()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
