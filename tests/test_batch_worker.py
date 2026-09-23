'''HomeIotManager - バッチワーカー 単体テスト'''

import asyncio

import pytest

from homeiot.services.batch_worker import BatchWorker


class TestBatchWorker:
    '''BatchWorker クラスの単体テスト'''

    @pytest.mark.asyncio
    async def test_batch_worker_init_defaults(self, mocker):
        '''引数なしで初期化した場合のテスト'''
        mocker.patch('homeiot.services.batch_worker.Config')
        mocker.patch('homeiot.services.batch_worker.DBConnector')
        mocker.patch('homeiot.services.batch_worker.HueClient')
        mocker.patch('homeiot.services.batch_worker.IftttClient')
        mock_hs = mocker.patch('homeiot.services.batch_worker.HomeService')

        worker = BatchWorker()

        assert worker.home_service == mock_hs.return_value
        assert worker.interval == 10
        assert worker._running is False

    @pytest.mark.asyncio
    async def test_batch_worker_run_and_stop(self, mocker):
        '''1回実行後に stop() された場合ループを正常終了するかテスト'''
        mock_home_service = mocker.MagicMock()
        mock_home_service.handle_presence_check = mocker.AsyncMock()

        worker = BatchWorker(home_service=mock_home_service)

        # 最初のループ中に stop() を呼ぶため、handle_presence_check のサイドエフェクトで worker.stop() を呼ぶ
        async def side_effect():
            worker.stop()

        mock_home_service.handle_presence_check.side_effect = side_effect

        # asyncio.sleep を即座に完了させるモック
        mocker.patch('asyncio.sleep', mocker.AsyncMock())

        await worker.run()

        mock_home_service.handle_presence_check.assert_called_once()
        assert worker._running is False

    @pytest.mark.asyncio
    async def test_batch_worker_run_exception_handling(self, mocker):
        '''handle_presence_check で例外が発生してもループが継続するかテスト'''
        mock_home_service = mocker.MagicMock()

        worker = BatchWorker(home_service=mock_home_service)

        calls = 0

        async def presence_check_side_effect():
            nonlocal calls
            calls += 1
            if calls == 1:
                raise Exception('DB Error')
            else:
                worker.stop()

        mock_home_service.handle_presence_check = mocker.AsyncMock(
            side_effect=presence_check_side_effect
        )

        mocker.patch('asyncio.sleep', mocker.AsyncMock())

        await worker.run()

        assert calls == 2

    @pytest.mark.asyncio
    async def test_batch_worker_run_cancelled_error(self, mocker):
        '''asyncio.sleep 中に CancelledError が発生した場合のテスト'''
        mock_home_service = mocker.MagicMock()
        mock_home_service.handle_presence_check = mocker.AsyncMock()

        worker = BatchWorker(home_service=mock_home_service)

        mocker.patch('asyncio.sleep', mocker.AsyncMock(side_effect=asyncio.CancelledError))

        await worker.run()

        mock_home_service.handle_presence_check.assert_called_once()
        assert worker._running is True

    @pytest.mark.asyncio
    async def test_batch_worker_signal_handler_exception(self, mocker):
        '''loop.add_signal_handler が Exception(NotImplementedError) を出す場合のテスト'''
        mock_home_service = mocker.MagicMock()
        mock_home_service.handle_presence_check = mocker.AsyncMock()

        worker = BatchWorker(home_service=mock_home_service)

        # add_signal_handler が NotImplementedError を投げるようにモック
        loop = asyncio.get_running_loop()
        mocker.patch.object(loop, 'add_signal_handler', side_effect=NotImplementedError)

        async def side_effect():
            worker.stop()

        mock_home_service.handle_presence_check.side_effect = side_effect
        mocker.patch('asyncio.sleep', mocker.AsyncMock())

        await worker.run()

        assert mock_home_service.handle_presence_check.call_count == 1
