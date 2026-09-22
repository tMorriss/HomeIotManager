'''HomeIotManager - データベースアクセス層単体テスト (非同期)
'''

import os
import unittest
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from homeiot.config import Config
from homeiot.db.connector import DBConnector, InOutValue, LastName


class TestDBConnector(unittest.IsolatedAsyncioTestCase):
    '''DBConnector クラスの単体テスト'''

    async def asyncSetUp(self):
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
        with patch.dict(os.environ, env):
            self.config = Config()
        self.db = DBConnector(config=self.config)

    async def asyncTearDown(self):
        await self.db.close()

    def _create_mock_pool(self, mock_cursor):
        mock_cursor.execute = AsyncMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_pool = MagicMock()
        mock_pool.closed = False
        mock_pool.wait_closed = AsyncMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        return mock_pool

    @patch('aiomysql.create_pool', new_callable=AsyncMock)
    async def test_get_pool_reuse_and_close(self, mock_create_pool):
        '''コネクションプールが再利用され、close で破棄されることの検証'''
        mock_pool = MagicMock()
        mock_pool.closed = False
        mock_pool.wait_closed = AsyncMock()
        mock_create_pool.return_value = mock_pool

        pool1 = await self.db.get_pool()
        pool2 = await self.db.get_pool()
        self.assertEqual(pool1, pool2)
        mock_create_pool.assert_called_once_with(
            host='mock_host',
            port=3306,
            user='mock_user',
            password='mock_pass',
            db='mock_db',
            autocommit=True,
        )

        await self.db.close()
        mock_pool.close.assert_called_once()
        mock_pool.wait_closed.assert_called_once()
        self.assertIsNone(self.db._pool)

    @patch('aiomysql.create_pool', new_callable=AsyncMock)
    async def test_get_last_found(self, mock_create_pool):
        '''LastName Enum を使用した get_last のレコード取得処理の検証'''
        now = datetime.now()
        mock_cursor = MagicMock()
        mock_cursor.fetchone = AsyncMock(return_value=(now,))
        mock_pool = self._create_mock_pool(mock_cursor)
        mock_create_pool.return_value = mock_pool

        res = await self.db.get_last(LastName.IN)
        self.assertEqual(res, now)
        mock_cursor.execute.assert_called_once()
        self.assertIn('SELECT time FROM lasts WHERE name = %s', mock_cursor.execute.call_args[0][0])
        self.assertEqual(mock_cursor.execute.call_args[0][1], (LastName.IN,))

    @patch('aiomysql.create_pool', new_callable=AsyncMock)
    async def test_get_last_not_found(self, mock_create_pool):
        '''get_last のレコードが存在しない場合の検証'''
        mock_cursor = MagicMock()
        mock_cursor.fetchone = AsyncMock(return_value=None)
        mock_pool = self._create_mock_pool(mock_cursor)
        mock_create_pool.return_value = mock_pool

        res = await self.db.get_last(LastName.OUT)
        self.assertIsNone(res)

    @patch('aiomysql.create_pool', new_callable=AsyncMock)
    async def test_set_last(self, mock_create_pool):
        '''LastName Enum を使用した set_last の保存処理の検証'''
        now = datetime.now()
        mock_cursor = MagicMock()
        mock_pool = self._create_mock_pool(mock_cursor)
        mock_create_pool.return_value = mock_pool

        await self.db.set_last(LastName.IN, now)
        mock_cursor.execute.assert_called_once()
        self.assertEqual(mock_cursor.execute.call_args[0][1], (LastName.IN, now))

    @patch('aiomysql.create_pool', new_callable=AsyncMock)
    async def test_set_last_default_now(self, mock_create_pool):
        '''set_last で日時未指定時に現在日時が使用されることの検証'''
        mock_cursor = MagicMock()
        mock_pool = self._create_mock_pool(mock_cursor)
        mock_create_pool.return_value = mock_pool

        await self.db.set_last(LastName.IN)
        mock_cursor.execute.assert_called_once()
        self.assertEqual(mock_cursor.execute.call_args[0][1][0], LastName.IN)
        self.assertIsInstance(mock_cursor.execute.call_args[0][1][1], datetime)

    @patch('aiomysql.create_pool', new_callable=AsyncMock)
    async def test_get_roomy_lock(self, mock_create_pool):
        '''get_roomy_lock の取得処理の検証'''
        today = date.today()
        mock_cursor = MagicMock()
        mock_cursor.fetchone = AsyncMock(return_value=(today,))
        mock_pool = self._create_mock_pool(mock_cursor)
        mock_create_pool.return_value = mock_pool

        res = await self.db.get_roomy_lock()
        self.assertEqual(res, today)

    @patch('aiomysql.create_pool', new_callable=AsyncMock)
    async def test_set_roomy_lock(self, mock_create_pool):
        '''set_roomy_lock の登録処理の検証'''
        today = date.today()
        mock_cursor = MagicMock()
        mock_pool = self._create_mock_pool(mock_cursor)
        mock_create_pool.return_value = mock_pool

        await self.db.set_roomy_lock(today)
        mock_cursor.execute.assert_called_once()
        self.assertEqual(mock_cursor.execute.call_args[0][1], (today,))

    @patch('aiomysql.create_pool', new_callable=AsyncMock)
    async def test_delete_roomy_lock(self, mock_create_pool):
        '''delete_roomy_lock で全削除が実行されることの検証'''
        mock_cursor = MagicMock()
        mock_pool = self._create_mock_pool(mock_cursor)
        mock_create_pool.return_value = mock_pool

        await self.db.delete_roomy_lock()
        mock_cursor.execute.assert_called_once_with('DELETE FROM roomy_lock')

    @patch('aiomysql.create_pool', new_callable=AsyncMock)
    async def test_add_in_out_log(self, mock_create_pool):
        '''InOutValue Enum を使用した add_in_out_log の追加処理の検証'''
        now = datetime.now()
        mock_cursor = MagicMock()
        mock_pool = self._create_mock_pool(mock_cursor)
        mock_create_pool.return_value = mock_pool

        await self.db.add_in_out_log(InOutValue.IN, now)
        mock_cursor.execute.assert_called_once()
        self.assertEqual(mock_cursor.execute.call_args[0][1], (now, InOutValue.IN))

    @patch('aiomysql.create_pool', new_callable=AsyncMock)
    async def test_add_in_out_log_default_now(self, mock_create_pool):
        '''add_in_out_log で日時未指定時に現在日時が使用されることの検証'''
        mock_cursor = MagicMock()
        mock_pool = self._create_mock_pool(mock_cursor)
        mock_create_pool.return_value = mock_pool

        await self.db.add_in_out_log(InOutValue.IN)
        mock_cursor.execute.assert_called_once()
        self.assertIsInstance(mock_cursor.execute.call_args[0][1][0], datetime)
        self.assertEqual(mock_cursor.execute.call_args[0][1][1], InOutValue.IN)


if __name__ == '__main__':
    unittest.main()
