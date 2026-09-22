'''HomeIotManager - 非同期 HTTP クライアント基底モジュール

httpx.AsyncClient のライフサイクル管理を提供する基底クラスです。
'''

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class BaseHttpClient:
    '''非同期 HTTP クライアント基底クラス'''

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self._client = client

    @property
    def client(self) -> httpx.AsyncClient:
        '''AsyncClient を取得（未作成またはクローズ時は再作成）します。'''
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient()
        return self._client

    async def close(self) -> None:
        '''AsyncClient をクローズします。'''
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
