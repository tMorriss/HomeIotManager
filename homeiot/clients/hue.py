'''HomeIotManager - Philips Hue REST API クライアントモジュール

宅内 Hue ブリッジとの通信を行い、グループやシーンの制御を非同期で行います。
httpx.AsyncClient による非同期 HTTP リクエストとコネクション再利用に対応しています。
'''

import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class HueClient:
    '''Philips Hue ローカル REST API クライアント (非同期)'''

    def __init__(
        self,
        bridge_ip: str,
        api_user: str,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.bridge_ip = bridge_ip
        self.api_user = api_user
        self.base_url = f'http://{self.bridge_ip}/api/{self.api_user}'
        self._client = client
        self._owns_client = client is None

    @property
    def client(self) -> httpx.AsyncClient:
        '''AsyncClient を取得（未作成またはクローズ時は再作成）します。'''
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient()
            self._owns_client = True
        return self._client

    async def close(self) -> None:
        '''AsyncClient をクローズします。'''
        if self._owns_client and self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def activate_scene(self, group_id: str, scene_id: str) -> bool:
        '''指定グループに対してシーンを呼び出します (PUT /groups/<id>/action)。'''
        url = f'{self.base_url}/groups/{group_id}/action'
        payload = {'scene': scene_id}
        try:
            res = await self.client.put(url, json=payload, timeout=5.0)
            res.raise_for_status()
            return True
        except Exception as e:
            logger.error(f'Failed to activate scene {scene_id} for group {group_id}: {e}')
            return False

    async def turn_off_group(self, group_id: str) -> bool:
        '''指定グループの消灯を行います (PUT /groups/<id>/action)。'''
        url = f'{self.base_url}/groups/{group_id}/action'
        payload = {'on': False}
        try:
            res = await self.client.put(url, json=payload, timeout=5.0)
            res.raise_for_status()
            return True
        except Exception as e:
            logger.error(f'Failed to turn off group {group_id}: {e}')
            return False

    async def get_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        '''指定グループの状態情報を取得します (GET /groups/<id>)。'''
        url = f'{self.base_url}/groups/{group_id}'
        try:
            res = await self.client.get(url, timeout=5.0)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            logger.error(f'Failed to get group {group_id}: {e}')
            return None

    async def is_any_on(self, group_id: str) -> Optional[bool]:
        '''指定グループ内のいずれかのライトが点灯中か判定します (.state.any_on)。'''
        group = await self.get_group(group_id)
        if group is None:
            return None
        state = group.get('state', {})
        if isinstance(state, dict) and 'any_on' in state:
            return bool(state['any_on'])
        return None
