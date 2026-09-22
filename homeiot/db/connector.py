'''HomeIotManager - データベースアクセス層モジュール

aiomysql を用いた MySQL データベースとの非同期接続およびクエリ実行を提供します。
'''

from datetime import date, datetime
from enum import Enum
from typing import Optional

import aiomysql

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
    '''MySQL データベースコネクタおよび DAO クラス (非同期)'''

    def __init__(self, config: Config):
        self.config = config
        self._pool: Optional[aiomysql.Pool] = None

    async def get_pool(self) -> aiomysql.Pool:
        '''aiomysql コネクションプールを取得（未作成またはクローズ時は再作成）します。'''
        if self._pool is None or self._pool.closed:
            self._pool = await aiomysql.create_pool(
                host=self.config.db_host,
                port=self.config.db_port,
                user=self.config.db_user,
                password=self.config.db_pass,
                db=self.config.db_name,
                autocommit=True,
            )
        return self._pool

    async def close(self) -> None:
        '''データベースコネクションプールを閉じます。'''
        if self._pool is not None and not self._pool.closed:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None

    async def get_last(self, name: LastName) -> Optional[datetime]:
        '''lasts テーブルから指定された名前の最終日時を取得します。'''
        query = 'SELECT time FROM lasts WHERE name = %s'
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, (name,))
                row = await cursor.fetchone()
                return row[0] if row else None

    async def set_last(self, name: LastName, event_time: Optional[datetime] = None) -> None:
        '''lasts テーブルに指定された名前の最終日時を保存（INSERT ON DUPLICATE KEY UPDATE）します。'''
        if event_time is None:
            event_time = datetime.now()
        query = '''
            INSERT INTO lasts (name, time)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE time = VALUES(time)
        '''
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, (name, event_time))

    async def get_roomy_lock(self) -> Optional[date]:
        '''roomy_lock テーブルから最新のルンバ稼働抑制日を取得します。'''
        query = 'SELECT date FROM roomy_lock ORDER BY date DESC LIMIT 1'
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query)
                row = await cursor.fetchone()
                return row[0] if row else None

    async def set_roomy_lock(self, lock_date: date) -> None:
        '''roomy_lock テーブルにルンバ稼働抑制日を登録または更新します。'''
        query = 'INSERT INTO roomy_lock (date) VALUES (%s) ON DUPLICATE KEY UPDATE date = VALUES(date)'
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, (lock_date,))

    async def delete_roomy_lock(self) -> None:
        '''roomy_lock テーブルからすべての抑制日を削除します。'''
        query = 'DELETE FROM roomy_lock'
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query)

    async def add_in_out_log(
        self, value: InOutValue, event_time: Optional[datetime] = None
    ) -> None:
        '''in_out テーブルに入退室ログ（0: 外出, 1: 帰宅）を追加します。'''
        if event_time is None:
            event_time = datetime.now()
        query = 'INSERT INTO in_out (datetime, value) VALUES (%s, %s)'
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, (event_time, value))
