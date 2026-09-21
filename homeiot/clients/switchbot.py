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
            'eventVersion': '1.0',
            'context': {
                'deviceType': 'WoPresence',
                'detectionState': 'DETECTED',
                'timeOfSample': 1625000000000
            }
        }
        '''
        if not isinstance(payload, dict):
            return {'is_motion_detected': False, 'device_type': None, 'detection_state': None}

        context = payload.get('context', {})
        if not isinstance(context, dict):
            context = {}

        device_type = context.get('deviceType') or payload.get('deviceType')
        detection_state = context.get('detectionState') or payload.get('detectionState')

        is_motion_detected = (
            device_type == 'WoPresence' and detection_state == 'DETECTED'
        )

        return {
            'is_motion_detected': is_motion_detected,
            'device_type': device_type,
            'detection_state': detection_state,
        }
