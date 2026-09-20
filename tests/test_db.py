'''HomeIotManager - データベースアクセス層単体テスト
'''

import unittest
from datetime import date, datetime
from unittest.mock import MagicMock, patch

from homeiot.config import Config
from homeiot.db.connector import DBConnector


class TestDBConnector(unittest.TestCase):
    '''DBConnector クラスの単体テスト'''

    def setUp(self):
        self.config = Config(
            db_host='mock_host',
            db_port=3306,
            db_user='mock_user',
            db_pass='mock_pass',
            db_name='mock_db',
        )
        self.db = DBConnector(config=self.config)

    @patch('mysql.connector.connect')
    def test_get_connection(self, mock_connect):
        '''mysql.connector.connect が正しいパラメータで呼び出されることの検証'''
        self.db.get_connection()
        mock_connect.assert_called_once_with(
            host='mock_host',
            port=3306,
            user='mock_user',
            password='mock_pass',
            database='mock_db',
            autocommit=True,
        )

    def test_init_without_config(self):
        '''Config オブジェクトなしで初期化した場合の動作検証'''
        db = DBConnector(host='custom_host', user='user', password='pass', database='db')
        self.assertEqual(db.host, 'custom_host')
        self.assertEqual(db.port, 3306)

    @patch('mysql.connector.connect')
    def test_get_last_found(self, mock_connect):
        '''get_last のレコードが存在する場合の検証'''
        now = datetime.now()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (now,)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        res = self.db.get_last('in')
        self.assertEqual(res, now)
        mock_cursor.execute.assert_called_once()
        self.assertIn('SELECT time FROM lasts WHERE name = %s', mock_cursor.execute.call_args[0][0])
        self.assertEqual(mock_cursor.execute.call_args[0][1], ('in',))

    @patch('mysql.connector.connect')
    def test_get_last_not_found(self, mock_connect):
        '''get_last のレコードが存在しない場合の検証'''
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        res = self.db.get_last('out')
        self.assertIsNone(res)

    @patch('mysql.connector.connect')
    def test_set_last(self, mock_connect):
        '''set_last で指定された日時が保存されることの検証'''
        now = datetime.now()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        self.db.set_last('in', now)
        mock_cursor.execute.assert_called_once()
        self.assertEqual(mock_cursor.execute.call_args[0][1], ('in', now))

    @patch('mysql.connector.connect')
    def test_set_last_default_now(self, mock_connect):
        '''set_last で日時未指定時に現在日時が使用されることの検証'''
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        self.db.set_last('in')
        mock_cursor.execute.assert_called_once()
        self.assertEqual(mock_cursor.execute.call_args[0][1][0], 'in')
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
    def test_delete_roomy_lock_specific_date(self, mock_connect):
        '''delete_roomy_lock で日付指定削除の検証'''
        today = date.today()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        self.db.delete_roomy_lock(today)
        mock_cursor.execute.assert_called_once()
        self.assertIn('WHERE date = %s', mock_cursor.execute.call_args[0][0])
        self.assertEqual(mock_cursor.execute.call_args[0][1], (today,))

    @patch('mysql.connector.connect')
    def test_delete_roomy_lock_all(self, mock_connect):
        '''delete_roomy_lock で全削除の検証'''
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        self.db.delete_roomy_lock()
        mock_cursor.execute.assert_called_once_with('DELETE FROM roomy_lock')

    @patch('mysql.connector.connect')
    def test_add_in_out_log(self, mock_connect):
        '''add_in_out_log でログが追加されることの検証'''
        now = datetime.now()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        self.db.add_in_out_log(1, now)
        mock_cursor.execute.assert_called_once()
        self.assertEqual(mock_cursor.execute.call_args[0][1], (now, 1))

    @patch('mysql.connector.connect')
    def test_get_recent_in_out_logs(self, mock_connect):
        '''get_recent_in_out_logs でログリストが返されることの検証'''
        now = datetime.now()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(now, 1), (now, 0)]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        logs = self.db.get_recent_in_out_logs(limit=5)
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0], {'datetime': now, 'value': 1})
        self.assertEqual(logs[1], {'datetime': now, 'value': 0})
        mock_cursor.execute.assert_called_once_with(
            'SELECT datetime, value FROM in_out ORDER BY datetime DESC LIMIT %s', (5,)
        )


if __name__ == '__main__':
    unittest.main()
