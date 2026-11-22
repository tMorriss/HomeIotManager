'''HomeIotManager - SwitchBot OpenAPI クライアント'''

import base64
import hashlib
import hmac
import logging
import time
import uuid
from typing import Any, Optional

import httpx

from homeiot import constants
from homeiot.clients.base import BaseHttpClient

logger = logging.getLogger(__name__)


class SwitchBotApiClient(BaseHttpClient):
    '''SwitchBot OpenAPI の汎用リクエストと状態確認を提供します。'''

    def __init__(
        self,
        token: str,
        secret: str,
        client: Optional[httpx.AsyncClient] = None,
    ):
        super().__init__(client=client)
        self.token = token
        self.secret = secret

    def _auth_headers(self) -> dict[str, str]:
        '''SwitchBot OpenAPI v1.1 の署名ヘッダーを生成します。'''
        timestamp = str(int(time.time() * 1000))
        nonce = str(uuid.uuid4())
        message = f'{self.token}{timestamp}{nonce}'.encode('utf-8')
        signature = hmac.new(
            self.secret.encode('utf-8'), message, hashlib.sha256
        ).digest()
        return {
            'Authorization': self.token,
            'sign': base64.b64encode(signature).decode('utf-8'),
            't': timestamp,
            'nonce': nonce,
        }

    async def request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        '''HTTP メソッド・パスを指定して OpenAPI を呼び出します。'''
        url = f'{constants.SWITCHBOT_API_BASE_URL}{path}'
        headers = dict(kwargs.pop('headers', {}) or {})
        headers.update(self._auth_headers())
        try:
            response = await self.client.request(
                method,
                url,
                timeout=constants.SWITCHBOT_API_TIMEOUT_SECONDS,
                headers=headers,
                **kwargs,
            )
            response.raise_for_status()
            return response
        except httpx.HTTPError:
            logger.exception('SwitchBot API request failed: %s %s', method, path)
            raise

    async def is_active(self, device_id: str) -> bool:
        '''デバイス状態取得 API が statusCode 100 を返した場合だけ active とします。'''
        try:
            response = await self.request(
                method='GET',
                path=f'/v1.1/devices/{device_id}/status',
            )
            body = response.json()
            return isinstance(body, dict) and body.get('statusCode') == 100
        except httpx.HTTPError:
            return False
        except ValueError:
            logger.exception('Failed to parse SwitchBot device status for %s.', device_id)
            return False
