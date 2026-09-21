'''HomeIotManager - Philips Hue REST API クライアントモジュール

宅内 Hue ブリッジとの通信を行い、グループやシーンの制御を行います。
常駐バッチ環境に配慮し requests.Session によるコネクション再利用に対応しています。
'''

import logging
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class HueClient:
    '''Philips Hue ローカル REST API クライアント'''

    def __init__(self, bridge_ip: str, api_user: str, session: Optional[requests.Session] = None):
        self.bridge_ip = bridge_ip
        self.api_user = api_user
        self.base_url = f'http://{self.bridge_ip}/api/{self.api_user}'
        self.session = session or requests.Session()

    def activate_scene(self, group_id: str, scene_id: str) -> bool:
        '''指定グループに対してシーンを呼び出します (PUT /groups/<id>/action)。'''
        url = f'{self.base_url}/groups/{group_id}/action'
        payload = {'scene': scene_id}
        try:
            res = self.session.put(url, json=payload, timeout=5)
            res.raise_for_status()
            return True
        except Exception as e:
            logger.error(f'Failed to activate scene {scene_id} for group {group_id}: {e}')
            return False

    def turn_off_group(self, group_id: str) -> bool:
        '''指定グループの消灯を行います (PUT /groups/<id>/action)。'''
        url = f'{self.base_url}/groups/{group_id}/action'
        payload = {'on': False}
        try:
            res = self.session.put(url, json=payload, timeout=5)
            res.raise_for_status()
            return True
        except Exception as e:
            logger.error(f'Failed to turn off group {group_id}: {e}')
            return False

    def get_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        '''指定グループの状態情報を取得します (GET /groups/<id>)。'''
        url = f'{self.base_url}/groups/{group_id}'
        try:
            res = self.session.get(url, timeout=5)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            logger.error(f'Failed to get group {group_id}: {e}')
            return None
