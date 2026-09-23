'''HomeIotManager - CLI 単体テスト'''

import argparse
import sys

from homeiot.cli import main, run_web, run_worker


class TestCli:
    '''CLI の単体テスト'''

    def test_run_web(self, mocker):
        '''run_web 関数のテスト'''
        mock_config_cls = mocker.patch('homeiot.cli.Config')
        mock_create_app = mocker.patch('homeiot.cli.create_app')
        mock_uvicorn_run = mocker.patch('uvicorn.run')

        args = argparse.Namespace(host='127.0.0.1', port=8000)
        run_web(args)

        mock_config_cls.assert_called_once()
        mock_create_app.assert_called_once_with(config=mock_config_cls.return_value)
        mock_uvicorn_run.assert_called_once_with(
            mock_create_app.return_value, host='127.0.0.1', port=8000
        )

    def test_run_worker(self, mocker):
        '''run_worker 関数のテスト'''
        mock_batch_worker_cls = mocker.patch('homeiot.cli.BatchWorker')
        mock_asyncio_run = mocker.patch('asyncio.run')

        args = argparse.Namespace()
        run_worker(args)

        mock_batch_worker_cls.assert_called_once()
        mock_asyncio_run.assert_called_once_with(mock_batch_worker_cls.return_value.run())

    def test_main_web_subcommand(self, mocker):
        '''main 関数で web サブコマンドを実行した場合のテスト'''
        mocker.patch.object(
            sys, 'argv', ['homeiot-cli', 'web', '--host', '0.0.0.0', '--port', '8930']
        )
        mock_run_web = mocker.patch('homeiot.cli.run_web')

        main()

        mock_run_web.assert_called_once()
        args = mock_run_web.call_args[0][0]
        assert args.host == '0.0.0.0'
        assert args.port == 8930

    def test_main_worker_subcommand(self, mocker):
        '''main 関数で worker サブコマンドを実行した場合のテスト'''
        mocker.patch.object(sys, 'argv', ['homeiot-cli', 'worker'])
        mock_run_worker = mocker.patch('homeiot.cli.run_worker')

        main()

        mock_run_worker.assert_called_once()

    def test_cli_main_block(self, mocker):
        '''cli モジュールの if __name__ == '__main__': ブロックのテスト'''
        mock_main = mocker.patch('homeiot.cli.main')

        code = compile("if __name__ == '__main__': main()", '<string>', 'exec')
        exec(code, {'__name__': '__main__', 'main': mock_main})

        mock_main.assert_called_once()
