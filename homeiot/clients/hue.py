'''HomeIotManager - Philips Hue REST API クライアントモジュール

宅内 Hue ブリッジとの通信を行い、グループやシーンの制御を非同期で行います。
httpx.AsyncClient による非同期 HTTP リクエストとコネクション再利用に対応しています。
'''

import logging
from typing import Any, Dict, Optional

import httpx

from homeiot import constants
from homeiot.clients.base import BaseHttpClient

logger = logging.getLogger(__name__)


class HueClient(BaseHttpClient):
    '''Philips Hue ローカル REST API クライアント (非同期)'''

    def __init__(
        self,
        bridge_ip: str,
        bridge_id: str,
        application_key: str,
        client: Optional[httpx.AsyncClient] = None,
    ):
        super().__init__(client=client)
        self.bridge_ip = bridge_ip
        self.bridge_id = bridge_id
        self.application_key = application_key
        self.base_url = f'https://{self.bridge_ip}/clip/v2'

    @property
    def client(self) -> httpx.AsyncClient:
        '''CA バンドルを使う AsyncClient を取得します。'''
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                verify=constants.HUE_CA_BUNDLE_PATH,
                headers=self._headers,
            )
        return self._client

    @property
    def _headers(self) -> Dict[str, str]:
        '''API キーと証明書に一致するホスト名を返します。'''
        return {
            'hue-application-key': self.application_key,
            'Host': self.bridge_id,
        }

    @property
    def _extensions(self) -> Dict[str, str]:
        '''固定 IP 接続で証明書と TLS SNI に使うホスト名を返します。'''
        return {'sni_hostname': self.bridge_id}

    async def activate_scene(self, scene_resource_id: str) -> bool:
        '''指定された v2 シーンリソースを呼び出します。'''
        try:
            url = f'{self.base_url}/resource/scene/{scene_resource_id}'
            res = await self.client.put(
                url,
                json={'recall': {'action': 'active'}},
                headers=self._headers,
                extensions=self._extensions,
                timeout=constants.HUE_API_TIMEOUT_SECONDS,
            )
            res.raise_for_status()
            return True
        except Exception as e:
            logger.error(f'Failed to activate scene {scene_resource_id}: {e}')
            return False

    async def turn_off_group(self, grouped_light_resource_id: str) -> bool:
        '''指定された v2 grouped_light リソースを消灯します。'''
        try:
            url = f'{self.base_url}/resource/grouped_light/{grouped_light_resource_id}'
            res = await self.client.put(
                url,
                json={'on': {'on': False}},
                headers=self._headers,
                extensions=self._extensions,
                timeout=constants.HUE_API_TIMEOUT_SECONDS,
            )
            res.raise_for_status()
            return True
        except Exception as e:
            logger.error(f'Failed to turn off group {grouped_light_resource_id}: {e}')
            return False

    async def get_group(self, grouped_light_resource_id: str) -> Optional[Dict[str, Any]]:
        '''指定された v2 grouped_light リソースの状態を取得します。'''
        try:
            url = f'{self.base_url}/resource/grouped_light/{grouped_light_resource_id}'
            res = await self.client.get(
                url,
                headers=self._headers,
                extensions=self._extensions,
                timeout=constants.HUE_API_TIMEOUT_SECONDS,
            )
            res.raise_for_status()
            resources = res.json().get('data', [])
            return resources[0] if resources else None
        except Exception as e:
            logger.error(f'Failed to get group {grouped_light_resource_id}: {e}')
            return None

    async def is_any_on(self, grouped_light_resource_id: str) -> Optional[bool]:
        '''指定グループ内のいずれかのライトが点灯中か判定します。'''
        group = await self.get_group(grouped_light_resource_id)
        if group is None:
            return None
        on_state = group.get('on', {})
        if isinstance(on_state, dict) and 'on' in on_state:
            return bool(on_state['on'])
        return None
