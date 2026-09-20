'''HomeIotManager - データベースアクセス層単体テスト
'''

import os
import unittest
from datetime import date, datetime
from unittest.mock import MagicMock, patch

from homeiot.config import Config
from homeiot.db.connector import DBConnector, InOutValue, LastName


class TestDBConnector(unittest.TestCase):
    '''DBConnector クラスの単体テスト'''

    def setUp(self):
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

    @patch('mysql.connector.connect')
    def test_get_connection_reuse(self, mock_connect):
        '''接続オブジェクトが再利用され、close で切断されることの検証'''
        mock_conn = MagicMock()
        mock_conn.is_connected.return_value = True
        mock_connect.return_value = mock_conn

        conn1 = self.db.get_connection()
        conn2 = self.db.get_connection()
        self.assertEqual(conn1, conn2)
        mock_connect.assert_called_once_with(
            host='mock_host',
            port=3306,
            user='mock_user',
            password='mock_pass',
            database='mock_db',
            autocommit=True,
        )

        self.db.close()
        mock_conn.close.assert_called_once()
        self.assertIsNone(self.db._conn)

    @patch('mysql.connector.connect')
    def test_get_last_found(self, mock_connect):
        '''LastName Enum を使用した get_last のレコード取得処理の検証'''
        now = datetime.now()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (now,)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        res = self.db.get_last(LastName.IN)
        self.assertEqual(res, now)
        mock_cursor.execute.assert_called_once()
        self.assertIn('SELECT time FROM lasts WHERE name = %s', mock_cursor.execute.call_args[0][0])
        self.assertEqual(mock_cursor.execute.call_args[0][1], (LastName.IN,))

    @patch('mysql.connector.connect')
    def test_get_last_not_found(self, mock_connect):
        '''get_last のレコードが存在しない場合の検証'''
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        res = self.db.get_last(LastName.OUT)
        self.assertIsNone(res)

    @patch('mysql.connector.connect')
    def test_set_last(self, mock_connect):
        '''LastName Enum を使用した set_last の保存処理の検証'''
        now = datetime.now()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        self.db.set_last(LastName.IN, now)
        mock_cursor.execute.assert_called_once()
        self.assertEqual(mock_cursor.execute.call_args[0][1], (LastName.IN, now))

    @patch('mysql.connector.connect')
    def test_set_last_default_now(self, mock_connect):
        '''set_last で日時未指定時に現在日時が使用されることの検証'''
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        self.db.set_last(LastName.IN)
        mock_cursor.execute.assert_called_once()
        self.assertEqual(mock_cursor.execute.call_args[0][1][0], LastName.IN)
        self.assertIsInstance(mock_cursor.execute.call_args[0][1][1], datetime)

    @patch('mysql.connector.connect')
    def test_get_roomy_lock(self, mock_connect):
        '''get_roomy_lock の取得処理の検証'''
        today = date.today()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (today,)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        res = self.db.get_roomy_lock()
        self.assertEqual(res, today)

    @patch('mysql.connector.connect')
    def test_set_roomy_lock(self, mock_connect):
        '''set_roomy_lock の登録処理の検証'''
        today = date.today()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        self.db.set_roomy_lock(today)
        mock_cursor.execute.assert_called_once()
        self.assertEqual(mock_cursor.execute.call_args[0][1], (today,))

    @patch('mysql.connector.connect')
    def test_delete_roomy_lock(self, mock_connect):
        '''delete_roomy_lock で全削除が実行されることの検証'''
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        self.db.delete_roomy_lock()
        mock_cursor.execute.assert_called_once_with('DELETE FROM roomy_lock')

    @patch('mysql.connector.connect')
    def test_add_in_out_log(self, mock_connect):
        '''InOutValue Enum を使用した add_in_out_log の追加処理の検証'''
        now = datetime.now()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        self.db.add_in_out_log(InOutValue.IN, now)
        mock_cursor.execute.assert_called_once()
        self.assertEqual(mock_cursor.execute.call_args[0][1], (now, InOutValue.IN))

    @patch('mysql.connector.connect')
    def test_add_in_out_log_default_now(self, mock_connect):
        '''add_in_out_log で日時未指定時に現在日時が使用されることの検証'''
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        self.db.add_in_out_log(InOutValue.IN)
        mock_cursor.execute.assert_called_once()
        self.assertIsInstance(mock_cursor.execute.call_args[0][1][0], datetime)
        self.assertEqual(mock_cursor.execute.call_args[0][1][1], InOutValue.IN)


if __name__ == '__main__':
    unittest.main()
