'''HomeIotManager - データベースアクセス層モジュール

MySQL データベースとの接続およびパラメータバインドを用いたクエリ実行を提供します。
'''

from datetime import date, datetime
from enum import Enum
from typing import Optional, Union

import mysql.connector

from homeiot.config import Config


class LastName(str, Enum):
    '''lasts テーブルのキー名'''

    IN = 'in'
    OUT = 'out'
    ROOMY = 'roomy'
    HUE_OFF = 'hue_off'


class InOutValue(int, Enum):
    '''in_out テーブルのイベント種別'''

    OUT = 0
    IN = 1


class DBConnector:
    '''MySQL データベースコネクタおよび DAO クラス'''

    def __init__(self, config: Config):
        self.config = config
        self._conn = None

    def get_connection(self):
        '''MySQL 接続オブジェクトを取得（未接続または切断時は再接続）します。'''
        if self._conn is None or not self._conn.is_connected():
            self._conn = mysql.connector.connect(
                host=self.config.db_host,
                port=self.config.db_port,
                user=self.config.db_user,
                password=self.config.db_pass,
                database=self.config.db_name,
                autocommit=True,
            )
        return self._conn

    def close(self):
        '''データベース接続を閉じます。'''
        if self._conn is not None and self._conn.is_connected():
            self._conn.close()
            self._conn = None

    def __del__(self):
        self.close()

    def get_last(self, name: Union[LastName, str]) -> Optional[datetime]:
        '''lasts テーブルから指定された名前の最終日時を取得します。'''
        key_name = name.value if isinstance(name, LastName) else name
        query = 'SELECT time FROM lasts WHERE name = %s'
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, (key_name,))
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            cursor.close()

    def set_last(self, name: Union[LastName, str], event_time: Optional[datetime] = None) -> None:
        '''lasts テーブルに指定された名前の最終日時を保存（INSERT ON DUPLICATE KEY UPDATE）します。'''
        key_name = name.value if isinstance(name, LastName) else name
        if event_time is None:
            event_time = datetime.now()
        query = '''
            INSERT INTO lasts (name, time)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE time = VALUES(time)
        '''
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, (key_name, event_time))
        finally:
            cursor.close()

    def get_roomy_lock(self) -> Optional[date]:
        '''roomy_lock テーブルから最新のルンバ稼働抑制日を取得します。'''
        query = 'SELECT date FROM roomy_lock ORDER BY date DESC LIMIT 1'
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query)
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            cursor.close()

    def set_roomy_lock(self, lock_date: date) -> None:
        '''roomy_lock テーブルにルンバ稼働抑制日を登録または更新します。'''
        query = 'INSERT INTO roomy_lock (date) VALUES (%s) ON DUPLICATE KEY UPDATE date = VALUES(date)'
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, (lock_date,))
        finally:
            cursor.close()

    def delete_roomy_lock(self) -> None:
        '''roomy_lock テーブルからすべての抑制日を削除します。'''
        query = 'DELETE FROM roomy_lock'
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query)
        finally:
            cursor.close()

    def add_in_out_log(self, value: Union[InOutValue, int], event_time: Optional[datetime] = None) -> None:
        '''in_out テーブルに入退室ログ（0: 外出, 1: 帰宅）を追加します。'''
        val = value.value if isinstance(value, InOutValue) else value
        if event_time is None:
            event_time = datetime.now()
        query = 'INSERT INTO in_out (datetime, value) VALUES (%s, %s)'
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, (event_time, val))
        finally:
            cursor.close()
