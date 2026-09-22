'''HomeIotManager - データベースアクセス層単体テスト (非同期)
'''

import os
from datetime import date, datetime

import pytest

from homeiot.config import Config
from homeiot.db.connector import DBConnector, InOutValue, LastName


class TestDBConnector:
    '''DBConnector クラスの単体テスト'''

    @pytest.fixture
    def db_connector(self, monkeypatch):
        env = {
            'DB_HOST': 'mock_host',
            'DB_PORT': '3306',
            'DB_USER': 'mock_user',
            'DB_PASS': 'mock_pass',
            'DB_NAME': 'mock_db',
            'TARGET_PHONE_IPS': '192.168.1.10',
            'HUE_BRIDGE_IP': '192.168.1.20',
            'HUE_API_USER': 'hueuser',
            'HUE_ON_SCENE_ID': 'scene123',
            'IFTTT_WEBHOOK_KEY': 'iftttkey',
            'SWITCHBOT_WEBHOOK_TOKEN': 'swtoken',
        }
        monkeypatch.setattr(os, 'environ', env)
        config = Config()
        return DBConnector(config=config)

    def _create_mock_pool(self, mock_cursor, mocker):
        mock_cursor.execute = mocker.AsyncMock()
        mock_conn = mocker.MagicMock()
        mock_conn.cursor.return_value.__aenter__ = mocker.AsyncMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__aexit__ = mocker.AsyncMock(return_value=None)

        mock_pool = mocker.MagicMock()
        mock_pool.closed = False
        mock_pool.wait_closed = mocker.AsyncMock()
        mock_pool.acquire.return_value.__aenter__ = mocker.AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = mocker.AsyncMock(return_value=None)
        return mock_pool

    @pytest.mark.asyncio
    async def test_get_pool_reuse_and_close(self, db_connector, mocker):
        '''コネクションプールが再利用され、close で破棄されることの検証'''
        mock_create_pool = mocker.patch('aiomysql.create_pool', new_callable=mocker.AsyncMock)
        mock_pool = mocker.MagicMock()
        mock_pool.closed = False
        mock_pool.wait_closed = mocker.AsyncMock()
        mock_create_pool.return_value = mock_pool

        pool1 = await db_connector.get_pool()
        pool2 = await db_connector.get_pool()
        assert pool1 == pool2
        mock_create_pool.assert_called_once_with(
            host='mock_host',
            port=3306,
            user='mock_user',
            password='mock_pass',
            db='mock_db',
            autocommit=True,
        )

        await db_connector.close()
        mock_pool.close.assert_called_once()
        mock_pool.wait_closed.assert_called_once()
        assert db_connector._pool is None

    @pytest.mark.asyncio
    async def test_get_last_found(self, db_connector, mocker):
        '''LastName Enum を使用した get_last のレコード取得処理の検証'''
        mock_create_pool = mocker.patch('aiomysql.create_pool', new_callable=mocker.AsyncMock)
        now = datetime.now()
        mock_cursor = mocker.MagicMock()
        mock_cursor.fetchone = mocker.AsyncMock(return_value=(now,))
        mock_pool = self._create_mock_pool(mock_cursor, mocker)
        mock_create_pool.return_value = mock_pool

        res = await db_connector.get_last(LastName.IN)
        assert res == now
        mock_cursor.execute.assert_called_once()
        assert 'SELECT time FROM lasts WHERE name = %s' in mock_cursor.execute.call_args[0][0]
        assert mock_cursor.execute.call_args[0][1] == (LastName.IN,)

    @pytest.mark.asyncio
    async def test_get_last_not_found(self, db_connector, mocker):
        '''get_last のレコードが存在しない場合の検証'''
        mock_create_pool = mocker.patch('aiomysql.create_pool', new_callable=mocker.AsyncMock)
        mock_cursor = mocker.MagicMock()
        mock_cursor.fetchone = mocker.AsyncMock(return_value=None)
        mock_pool = self._create_mock_pool(mock_cursor, mocker)
        mock_create_pool.return_value = mock_pool

        res = await db_connector.get_last(LastName.OUT)
        assert res is None

    @pytest.mark.asyncio
    async def test_set_last(self, db_connector, mocker):
        '''LastName Enum を使用した set_last の保存処理の検証'''
        mock_create_pool = mocker.patch('aiomysql.create_pool', new_callable=mocker.AsyncMock)
        now = datetime.now()
        mock_cursor = mocker.MagicMock()
        mock_pool = self._create_mock_pool(mock_cursor, mocker)
        mock_create_pool.return_value = mock_pool

        await db_connector.set_last(LastName.IN, now)
        mock_cursor.execute.assert_called_once()
        assert mock_cursor.execute.call_args[0][1] == (LastName.IN, now)

    @pytest.mark.asyncio
    async def test_set_last_default_now(self, db_connector, mocker):
        '''set_last で日時未指定時に現在日時が使用されることの検証'''
        mock_create_pool = mocker.patch('aiomysql.create_pool', new_callable=mocker.AsyncMock)
        mock_cursor = mocker.MagicMock()
        mock_pool = self._create_mock_pool(mock_cursor, mocker)
        mock_create_pool.return_value = mock_pool

        await db_connector.set_last(LastName.IN)
        mock_cursor.execute.assert_called_once()
        assert mock_cursor.execute.call_args[0][1][0] == LastName.IN
        assert isinstance(mock_cursor.execute.call_args[0][1][1], datetime)

    @pytest.mark.asyncio
    async def test_get_roomy_lock(self, db_connector, mocker):
        '''get_roomy_lock の取得処理の検証'''
        mock_create_pool = mocker.patch('aiomysql.create_pool', new_callable=mocker.AsyncMock)
        today = date.today()
        mock_cursor = mocker.MagicMock()
        mock_cursor.fetchone = mocker.AsyncMock(return_value=(today,))
        mock_pool = self._create_mock_pool(mock_cursor, mocker)
        mock_create_pool.return_value = mock_pool

        res = await db_connector.get_roomy_lock()
        assert res == today

    @pytest.mark.asyncio
    async def test_set_roomy_lock(self, db_connector, mocker):
        '''set_roomy_lock の登録処理の検証'''
        mock_create_pool = mocker.patch('aiomysql.create_pool', new_callable=mocker.AsyncMock)
        today = date.today()
        mock_cursor = mocker.MagicMock()
        mock_pool = self._create_mock_pool(mock_cursor, mocker)
        mock_create_pool.return_value = mock_pool

        await db_connector.set_roomy_lock(today)
        mock_cursor.execute.assert_called_once()
        assert mock_cursor.execute.call_args[0][1] == (today,)

    @pytest.mark.asyncio
    async def test_delete_roomy_lock(self, db_connector, mocker):
        '''delete_roomy_lock で全削除が実行されることの検証'''
        mock_create_pool = mocker.patch('aiomysql.create_pool', new_callable=mocker.AsyncMock)
        mock_cursor = mocker.MagicMock()
        mock_pool = self._create_mock_pool(mock_cursor, mocker)
        mock_create_pool.return_value = mock_pool

        await db_connector.delete_roomy_lock()
        mock_cursor.execute.assert_called_once_with('DELETE FROM roomy_lock')

    @pytest.mark.asyncio
    async def test_add_in_out_log(self, db_connector, mocker):
        '''InOutValue Enum を使用した add_in_out_log の追加処理の検証'''
        mock_create_pool = mocker.patch('aiomysql.create_pool', new_callable=mocker.AsyncMock)
        now = datetime.now()
        mock_cursor = mocker.MagicMock()
        mock_pool = self._create_mock_pool(mock_cursor, mocker)
        mock_create_pool.return_value = mock_pool

        await db_connector.add_in_out_log(InOutValue.IN, now)
        mock_cursor.execute.assert_called_once()
        assert mock_cursor.execute.call_args[0][1] == (now, InOutValue.IN)

    @pytest.mark.asyncio
    async def test_add_in_out_log_default_now(self, db_connector, mocker):
        '''add_in_out_log で日時未指定時に現在日時が使用されることの検証'''
        mock_create_pool = mocker.patch('aiomysql.create_pool', new_callable=mocker.AsyncMock)
        mock_cursor = mocker.MagicMock()
        mock_pool = self._create_mock_pool(mock_cursor, mocker)
        mock_create_pool.return_value = mock_pool

        await db_connector.add_in_out_log(InOutValue.IN)
        mock_cursor.execute.assert_called_once()
        assert isinstance(mock_cursor.execute.call_args[0][1][0], datetime)
        assert mock_cursor.execute.call_args[0][1][1] == InOutValue.IN
