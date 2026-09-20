'''HomeIotManager - データベースアクセス層モジュール

MySQL データベースとの接続およびパラメータバインドを用いたクエリ実行を提供します。
'''

from datetime import date, datetime
from typing import Any, Dict, List, Optional

import mysql.connector

from homeiot.config import Config


class DBConnector:
    '''MySQL データベースコネクタおよび DAO クラス'''

    def __init__(
        self,
        config: Optional[Config] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        if config:
            self.host = host or config.db_host
            self.port = port or config.db_port
            self.user = user or config.db_user
            self.password = password or config.db_pass
            self.database = database or config.db_name
        else:
            self.host = host or 'localhost'
            self.port = port or 3306
            self.user = user or ''
            self.password = password or ''
            self.database = database or ''

    def get_connection(self):
        '''MySQL 接続オブジェクトを取得します。'''
        return mysql.connector.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            autocommit=True,
        )

    def get_last(self, name: str) -> Optional[datetime]:
        '''lasts テーブルから指定された名前の最終日時を取得します。'''
        query = 'SELECT time FROM lasts WHERE name = %s'
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            try:
                cursor.execute(query, (name,))
                row = cursor.fetchone()
                return row[0] if row else None
            finally:
                cursor.close()
        finally:
            conn.close()

    def set_last(self, name: str, event_time: Optional[datetime] = None) -> None:
        '''lasts テーブルに指定された名前の最終日時を保存（INSERT ON DUPLICATE KEY UPDATE）します。'''
        if event_time is None:
            event_time = datetime.now()
        query = '''
            INSERT INTO lasts (name, time)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE time = VALUES(time)
        '''
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            try:
                cursor.execute(query, (name, event_time))
            finally:
                cursor.close()
        finally:
            conn.close()

    def get_roomy_lock(self) -> Optional[date]:
        '''roomy_lock テーブルから最新のルンバ稼働抑制日を取得します。'''
        query = 'SELECT date FROM roomy_lock ORDER BY date DESC LIMIT 1'
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            try:
                cursor.execute(query)
                row = cursor.fetchone()
                return row[0] if row else None
            finally:
                cursor.close()
        finally:
            conn.close()

    def set_roomy_lock(self, lock_date: date) -> None:
        '''roomy_lock テーブルにルンバ稼働抑制日を登録または更新します。'''
        query = 'INSERT INTO roomy_lock (date) VALUES (%s) ON DUPLICATE KEY UPDATE date = VALUES(date)'
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            try:
                cursor.execute(query, (lock_date,))
            finally:
                cursor.close()
        finally:
            conn.close()

    def delete_roomy_lock(self, lock_date: Optional[date] = None) -> None:
        '''roomy_lock テーブルから抑制日を削除します（指定なしの場合は全削除）。'''
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            try:
                if lock_date:
                    query = 'DELETE FROM roomy_lock WHERE date = %s'
                    cursor.execute(query, (lock_date,))
                else:
                    query = 'DELETE FROM roomy_lock'
                    cursor.execute(query)
            finally:
                cursor.close()
        finally:
            conn.close()

    def add_in_out_log(self, value: int, event_time: Optional[datetime] = None) -> None:
        '''in_out テーブルに入退室ログ（0: 外出, 1: 帰宅）を追加します。'''
        if event_time is None:
            event_time = datetime.now()
        query = 'INSERT INTO in_out (datetime, value) VALUES (%s, %s)'
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            try:
                cursor.execute(query, (event_time, value))
            finally:
                cursor.close()
        finally:
            conn.close()

    def get_recent_in_out_logs(self, limit: int = 10) -> List[Dict[str, Any]]:
        '''in_out テーブルから直近のログを取得します。'''
        query = 'SELECT datetime, value FROM in_out ORDER BY datetime DESC LIMIT %s'
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            try:
                cursor.execute(query, (limit,))
                rows = cursor.fetchall()
                return [{'datetime': row[0], 'value': row[1]} for row in rows]
            finally:
                cursor.close()
        finally:
            conn.close()
