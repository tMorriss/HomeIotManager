'''HomeIotManager - CLI 単体テスト'''

from unittest.mock import MagicMock, patch

import pytest

from homeiot import cli


class TestCLI:
    '''CLI エントリーポイントのテスト'''

    @patch('homeiot.cli.BatchWorker')
    @patch('asyncio.run')
    def test_main_worker_subcommand(self, mock_asyncio_run, mock_batch_worker):
        '''worker サブコマンドで BatchWorker.start が非同期実行されることの検証'''
        mock_worker_instance = MagicMock()
        mock_batch_worker.return_value = mock_worker_instance

        cli.main(['worker'])

        mock_batch_worker.assert_called_once()
        mock_asyncio_run.assert_called_once_with(mock_worker_instance.start())

    @patch('uvicorn.run')
    def test_main_web_subcommand_defaults(self, mock_uvicorn_run):
        '''web サブコマンドでデフォルト引数が uvicorn.run に渡されることの検証'''
        cli.main(['web'])

        mock_uvicorn_run.assert_called_once_with(
            'homeiot.app:create_app',
            factory=True,
            host='0.0.0.0',
            port=8001,
        )

    @patch('uvicorn.run')
    def test_main_web_subcommand_custom_args(self, mock_uvicorn_run):
        '''web サブコマンドでカスタム --host と --port が正しく渡されることの検証'''
        cli.main(['web', '--host', '127.0.0.1', '--port', '9000'])

        mock_uvicorn_run.assert_called_once_with(
            'homeiot.app:create_app',
            factory=True,
            host='127.0.0.1',
            port=9000,
        )

    def test_main_invalid_subcommand(self):
        '''無効なサブコマンドで SystemExit が発生することの検証'''
        with pytest.raises(SystemExit):
            cli.main(['invalid'])

    def test_main_block_execution(self, monkeypatch):
        '''if __name__ == "__main__" ブロックの実行テスト'''
        monkeypatch.setenv('DB_HOST', 'localhost')
        monkeypatch.setenv('DB_PORT', '3306')
        monkeypatch.setenv('DB_USER', 'root')
        monkeypatch.setenv('DB_PASS', 'pass')
        monkeypatch.setenv('DB_NAME', 'homeiot')
        monkeypatch.setenv('TARGET_PHONE_IPS', '192.168.111.51')
        monkeypatch.setenv('HUE_BRIDGE_IP', '192.168.111.100')
        monkeypatch.setenv('HUE_API_USER', 'hueuser')
        monkeypatch.setenv('HUE_ON_SCENE_ID', 'scene1')
        monkeypatch.setenv('IFTTT_WEBHOOK_KEY', 'iftttkey')
        monkeypatch.setenv('SWITCHBOT_WEBHOOK_TOKEN', 'token123')

        with patch('sys.argv', ['homeiot', 'worker']):
            with patch('homeiot.services.batch_worker.BatchWorker') as mock_worker:
                with patch('asyncio.run') as mock_asyncio_run:
                    globs = {'__name__': '__main__'}
                    exec(compile(open('homeiot/cli.py').read(), 'homeiot/cli.py', 'exec'), globs)
                    mock_worker.assert_called_once()
                    mock_asyncio_run.assert_called_once()
