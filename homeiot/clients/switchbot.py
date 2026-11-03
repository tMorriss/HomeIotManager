'''HomeIotManager - SwitchBot クライアント / ペイロード解析モジュール

SwitchBot Cloud から受信した Webhook ペイロードの検証・解析を行います。
'''

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SwitchBotClient:
    '''SwitchBot Webhook ペイロード検証・解析機能を提供するクライアント類'''

    def __init__(self, webhook_token: str):
        self.webhook_token = webhook_token

    def verify_token(self, token: Optional[str]) -> bool:
        '''Webhook リクエストから渡されたトークンが設定値と一致するか検証します。'''
        if not token or not self.webhook_token:
            return False
        return token.strip() == self.webhook_token.strip()

    def parse_webhook_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        '''SwitchBot 人感センサー (WoPresence) などの Webhook ペイロードを解析します。

        例:
        {
            'eventType': 'changeReport',
            'eventVersion': '1',
            'context': {
                'deviceType': 'WoPresence',
                'detectionState': 'DETECTED',
                'timeOfSample': 1625000000000
            }
        }
        '''
        if not isinstance(payload, dict):
            return {
                'is_valid': False,
                'is_motion_detected': False,
                'device_type': None,
                'detection_state': None,
                'error': 'invalid payload',
            }

        if payload.get('eventType') != 'changeReport':
            return {
                'is_valid': False,
                'is_motion_detected': False,
                'device_type': None,
                'detection_state': None,
                'error': 'invalid eventType',
            }

        if payload.get('eventVersion') != '1':
            return {
                'is_valid': False,
                'is_motion_detected': False,
                'device_type': None,
                'detection_state': None,
                'error': 'invalid eventVersion',
            }

        context = payload.get('context')
        if not isinstance(context, dict):
            return {
                'is_valid': False,
                'is_motion_detected': False,
                'device_type': None,
                'detection_state': None,
                'error': 'missing context',
            }

        device_type = context.get('deviceType')
        detection_state = context.get('detectionState')
        if device_type is None or detection_state is None:
            return {
                'is_valid': False,
                'is_motion_detected': False,
                'device_type': device_type,
                'detection_state': detection_state,
                'error': 'missing context fields',
            }

        is_motion_detected = (
            device_type == 'WoPresence' and detection_state == 'DETECTED'
        )

        return {
            'is_valid': True,
            'is_motion_detected': is_motion_detected,
            'device_type': device_type,
            'detection_state': detection_state,
            'error': None,
        }
