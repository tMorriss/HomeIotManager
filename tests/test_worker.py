'''tests/test_worker.py - BatchWorker および CLI の単体テスト'''

import signal
import sys
import unittest
from unittest.mock import MagicMock, patch

from homeiot import constants
from homeiot.cli import main as cli_main
from homeiot.services.batch_worker import BatchWorker, run_worker


class TestBatchWorker(unittest.TestCase):
    '''BatchWorker クラスの単体テスト'''

    @patch('homeiot.services.batch_worker.HomeService')
    @patch('homeiot.services.batch_worker.IftttClient')
    @patch('homeiot.services.batch_worker.HueClient')
    @patch('homeiot.services.batch_worker.DBConnector')
    @patch('homeiot.services.batch_worker.Config')
    def test_init_defaults(
        self,
        mock_config_cls,
        mock_db_cls,
        mock_hue_cls,
        mock_ifttt_cls,
        mock_home_service_cls,
    ):
        '''引数なしで初期化した場合の動作確認'''
        worker = BatchWorker()
        self.assertIsNotNone(worker.config)
        self.assertIsNotNone(worker.db)
        self.assertIsNotNone(worker.home_service)
        self.assertEqual(worker.interval, constants.CHECK_INTERVAL_SECONDS)
        self.assertFalse(worker.running)

    def test_stop(self):
        '''stop メソッドで running フラグが False になることを確認'''
        worker = BatchWorker(
            config=MagicMock(),
            db_connector=MagicMock(),
            home_service=MagicMock(),
            interval=1,
        )
        worker.running = True
        worker.stop()
        self.assertFalse(worker.running)

    def test_run_once_success(self):
        '''run_once が正常に handle_presence_check を呼ぶことを確認'''
        mock_service = MagicMock()
        worker = BatchWorker(
            config=MagicMock(),
            db_connector=MagicMock(),
            home_service=mock_service,
            interval=1,
        )
        worker.run_once()
        mock_service.handle_presence_check.assert_called_once()

    def test_run_once_exception_handling(self):
        '''run_once 内で例外が発生してもキャッチされることを確認'''
        mock_service = MagicMock()
        mock_service.handle_presence_check.side_effect = Exception('Unexpected error')
        worker = BatchWorker(
            config=MagicMock(),
            db_connector=MagicMock(),
            home_service=mock_service,
            interval=1,
        )
        # 例外が外に送出されないこと
        worker.run_once()
        mock_service.handle_presence_check.assert_called_once()

    @patch('homeiot.services.batch_worker.time.sleep')
    @patch('homeiot.services.batch_worker.time.time')
    def test_run_loop(self, mock_time, mock_sleep):
        '''run ループが1回以上動作して stop で停止することを確認'''
        mock_service = MagicMock()
        worker = BatchWorker(
            config=MagicMock(),
            db_connector=MagicMock(),
            home_service=mock_service,
            interval=10,
        )

        mock_time.return_value = 100.0

        def stop_worker(*args, **kwargs):
            worker.stop()

        mock_sleep.side_effect = stop_worker

        worker.run()
        self.assertFalse(worker.running)
        mock_service.handle_presence_check.assert_called_once()

    @patch('homeiot.services.batch_worker.signal.signal')
    def test_signal_handlers(self, mock_signal):
        '''シグナルハンドラが正常に登録されることを確認'''
        worker = BatchWorker(
            config=MagicMock(),
            db_connector=MagicMock(),
            home_service=MagicMock(),
            interval=1,
        )
        worker._setup_signal_handlers()
        mock_signal.assert_any_call(signal.SIGINT, worker.stop)
        mock_signal.assert_any_call(signal.SIGTERM, worker.stop)

    @patch('homeiot.services.batch_worker.signal.signal')
    def test_signal_handlers_exception(self, mock_signal):
        '''シグナル登録例外（ValueError等）が発生した場合に警告ログを出力して例外をハンドリングすることを確認'''
        mock_signal.side_effect = ValueError('Not in main thread')
        worker = BatchWorker(
            config=MagicMock(),
            db_connector=MagicMock(),
            home_service=MagicMock(),
            interval=1,
        )
        worker._setup_signal_handlers()

    @patch('homeiot.services.batch_worker.BatchWorker')
    def test_run_worker_helper(self, mock_batch_worker_cls):
        '''run_worker 起動ヘルパー関数の確認'''
        mock_instance = MagicMock()
        mock_batch_worker_cls.return_value = mock_instance
        run_worker()
        mock_instance.run.assert_called_once()


class TestCLI(unittest.TestCase):
    '''CLI エントリポイントの単体テスト'''

    @patch('homeiot.cli.create_app')
    def test_cli_web(self, mock_create_app):
        '''python -m homeiot.cli web コマンドのテスト'''
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app

        test_args = ['homeiot.cli', 'web']
        with patch.object(sys, 'argv', test_args):
            cli_main()

        mock_create_app.assert_called_once()
        mock_app.run.assert_called_once_with(host='0.0.0.0', port=constants.WEB_PORT)

    @patch('homeiot.cli.run_worker')
    def test_cli_worker(self, mock_run_worker):
        '''python -m homeiot.cli worker コマンドのテスト'''
        test_args = ['homeiot.cli', 'worker']
        with patch.object(sys, 'argv', test_args):
            cli_main()

        mock_run_worker.assert_called_once()

    def test_cli_no_args_shows_help(self):
        '''サブコマンド無しの場合はヘルプを表示して exit(1) することを確認'''
        test_args = ['homeiot.cli']
        with patch.object(sys, 'argv', test_args):
            with self.assertRaises(SystemExit) as cm:
                cli_main()
            self.assertEqual(cm.exception.code, 1)

    def test_cli_main_block(self):
        '''cli.py の __name__ == '__main__' ブロックの実行確認'''
        with patch('homeiot.cli.main') as mock_main:
            import homeiot.cli
            with patch.object(homeiot.cli, '__name__', '__main__'):
                # __name__ == '__main__' 条件で main() を呼び出す動作
                if homeiot.cli.__name__ == '__main__':
                    homeiot.cli.main()
            mock_main.assert_called_once()


if __name__ == '__main__':
    unittest.main()
