'''HomeIotManager - BatchWorker 単体テスト'''

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeiot.services.batch_worker import BatchWorker


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
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


@pytest.mark.asyncio
class TestBatchWorker:
    '''BatchWorker クラスの動作検証'''

    async def test_init_default(self):
        '''引数なし初期化時にデフォルト設定が生成されることの検証'''
        worker = BatchWorker()
        assert worker.config is not None
        assert worker.db is not None
        assert worker.home_service is not None
        assert worker.interval == 10
        assert worker.running is False

    async def test_init_custom(self):
        '''カスタム依存関係を注入して初期化できることの検証'''
        mock_config = MagicMock()
        mock_db = AsyncMock()
        mock_service = AsyncMock()

        worker = BatchWorker(
            config=mock_config,
            db_connector=mock_db,
            home_service=mock_service,
            interval=5,
        )
        assert worker.config == mock_config
        assert worker.db == mock_db
        assert worker.home_service == mock_service
        assert worker.interval == 5

    async def test_run_once_success(self):
        '''run_once が home_service.handle_presence_check を呼び出すことの検証'''
        mock_service = AsyncMock()
        worker = BatchWorker(home_service=mock_service)

        await worker.run_once()
        mock_service.handle_presence_check.assert_awaited_once()

    async def test_run_once_exception_handled(self, caplog):
        '''run_once 内での例外発生時にログが出力され、例外が捕捉されることの検証'''
        mock_service = AsyncMock()
        mock_service.handle_presence_check.side_effect = Exception('Presence check error')
        worker = BatchWorker(home_service=mock_service)

        await worker.run_once()
        assert 'Error occurred during presence check' in caplog.text

    async def test_start_loop_and_stop(self):
        '''start 実行後に一定回数ループが動作し、request_stop で安全に停止することの検証'''
        mock_service = AsyncMock()
        mock_db = AsyncMock()
        worker = BatchWorker(
            home_service=mock_service,
            db_connector=mock_db,
            interval=1,
        )

        call_count = 0

        async def fake_check():
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                worker.request_stop()

        mock_service.handle_presence_check.side_effect = fake_check

        await worker.start()

        assert call_count == 2
        assert worker.running is False
        mock_db.close.assert_awaited_once()

    async def test_setup_signal_handlers(self):
        '''_setup_signal_handlers が例外なく実行されることの検証'''
        worker = BatchWorker()
        worker._setup_signal_handlers()

    async def test_setup_signal_handlers_not_implemented(self):
        '''add_signal_handler が NotImplementedError を投げても捕捉されることの検証'''
        worker = BatchWorker()
        with patch('asyncio.get_running_loop') as mock_get_loop:
            mock_loop = MagicMock()
            mock_loop.add_signal_handler.side_effect = NotImplementedError
            mock_get_loop.return_value = mock_loop
            worker._setup_signal_handlers()

    async def test_stop(self):
        '''stop メソッドがリソースのクローズを呼び出すことの検証'''
        mock_db = AsyncMock()
        worker = BatchWorker(db_connector=mock_db)
        worker.running = True

        await worker.stop()
        assert worker.running is False
        mock_db.close.assert_awaited_once()
