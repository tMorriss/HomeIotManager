'''HomeIotManager - BatchWorker 単体テスト'''

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeiot.db.connector import LastName
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
    monkeypatch.setenv('HUE_BRIDGE_ID', 'bridge-id')
    monkeypatch.setenv('HUE_APPLICATION_KEY', 'application-key')
    monkeypatch.setenv('HUE_ON_GROUPED_LIGHT_RESOURCE_ID', 'on-group-id')
    monkeypatch.setenv('HUE_OFF_GROUPED_LIGHT_RESOURCE_ID', 'off-group-id')
    monkeypatch.setenv('HUE_ON_SCENE_RESOURCE_ID', 'scene-id')
    monkeypatch.setenv('IFTTT_WEBHOOK_KEY', 'iftttkey')
    monkeypatch.setenv('SWITCHBOT_WEBHOOK_TOKEN', 'token123')
    monkeypatch.setenv('SWITCHBOT_API_TOKEN', 'api-token')
    monkeypatch.setenv('SWITCHBOT_API_SECRET', 'api-secret')
    monkeypatch.setenv('PRESENCE_SENSOR_DEVICE_ID', 'sensor-123')


@pytest.mark.asyncio
class TestBatchWorker:
    '''BatchWorker クラスの動作検証'''

    async def test_init_default(self):
        '''引数なし初期化時にデフォルト設定が生成されることの検証'''
        worker = BatchWorker()
        assert worker.config is not None
        assert worker.db is not None
        assert worker.home_service is not None
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
        )
        assert worker.config == mock_config
        assert worker.db == mock_db
        assert worker.home_service == mock_service

    async def test_run_presence_check_once_success(self):
        '''run_presence_check_once が home_service.handle_presence_check を呼び出すことの検証'''
        mock_service = AsyncMock()
        worker = BatchWorker(home_service=mock_service)

        await worker.run_presence_check_once()
        mock_service.handle_presence_check.assert_awaited_once()

    @pytest.mark.parametrize(
        ('active', 'last_name'),
        [
            (True, LastName.PRESENCE_SENSOR_ACTIVE),
            (False, LastName.PRESENCE_SENSOR_INACTIVE),
        ],
    )
    async def test_check_presence_sensor_health_records_status(self, active, last_name):
        mock_config = MagicMock()
        mock_config.switchbot_api_token = 'api-token'
        mock_config.switchbot_api_secret = 'api-secret'
        mock_config.presence_sensor_device_id = 'sensor-123'
        mock_db = AsyncMock()
        mock_api = AsyncMock()
        mock_api.is_active.return_value = active
        worker = BatchWorker(
            config=mock_config,
            db_connector=mock_db,
            home_service=AsyncMock(),
            switchbot_api_client=mock_api,
        )

        await worker.check_presence_sensor_health()

        mock_api.is_active.assert_awaited_once_with('sensor-123')
        recorded_name, recorded_time = mock_db.set_last.await_args.args
        assert recorded_name == last_name
        assert recorded_time is not None

    async def test_check_presence_sensor_health_records_inactive_on_error(self):
        mock_config = MagicMock()
        mock_config.presence_sensor_device_id = 'sensor-123'
        mock_db = AsyncMock()
        mock_api = AsyncMock()
        mock_api.is_active.side_effect = RuntimeError('API failure')
        worker = BatchWorker(
            config=mock_config,
            db_connector=mock_db,
            home_service=AsyncMock(),
            switchbot_api_client=mock_api,
        )

        await worker.check_presence_sensor_health()

        mock_db.set_last.assert_awaited_once()
        assert mock_db.set_last.await_args.args[0] == LastName.PRESENCE_SENSOR_INACTIVE

    async def test_run_presence_check_once_exception_handled(self, caplog):
        '''在室確認中の例外がログに記録され、捕捉されることの検証'''
        mock_service = AsyncMock()
        mock_service.handle_presence_check.side_effect = Exception('Presence check error')
        worker = BatchWorker(home_service=mock_service)

        await worker.run_presence_check_once()
        assert 'Error occurred during presence check' in caplog.text

    async def test_periodic_loop_logs_operation_error_and_continues(self, monkeypatch, caplog):
        worker = BatchWorker()
        worker.running = True

        async def fail_operation():
            raise RuntimeError('periodic operation failed')

        async def stop_after_first_wait(awaitable, timeout):
            awaitable.close()
            worker.running = False
            raise asyncio.TimeoutError

        monkeypatch.setattr('asyncio.wait_for', stop_after_first_wait)

        await worker._run_periodic_loop(1, fail_operation, 'test_loop')

        assert 'Error occurred in test_loop loop' in caplog.text

    async def test_start_loop_and_stop(self, monkeypatch):
        '''start 実行後に一定回数ループが動作し、request_stop で安全に停止することの検証'''
        mock_service = AsyncMock()
        mock_db = AsyncMock()
        mock_api = AsyncMock()
        monkeypatch.setattr('homeiot.constants.PRESENCE_CHECK_INTERVAL_SECONDS', 1)
        worker = BatchWorker(
            home_service=mock_service,
            db_connector=mock_db,
            switchbot_api_client=mock_api,
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
        mock_api.is_active.assert_awaited_once_with('sensor-123')
        mock_db.close.assert_awaited_once()
        mock_api.close.assert_awaited_once()

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
