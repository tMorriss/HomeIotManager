'''HomeIotManager - SwitchBot クライアント / ペイロード解析モジュール

SwitchBot Cloud から受信した Webhook ペイロードの検証・解析を行います。
'''

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SwitchBotWebhookResult:
    '''SwitchBot Webhook ペイロードの解析結果'''

    is_valid: bool
    is_motion_detected: bool
    device_type: Optional[object] = None
    detection_state: Optional[object] = None
    error: Optional[str] = None


class SwitchBotClient:
    '''SwitchBot Webhook ペイロード検証・解析機能を提供するクライアント類'''

    def __init__(self, webhook_token: str):
        self.webhook_token = webhook_token

    def verify_token(self, token: Optional[str]) -> bool:
        '''Webhook リクエストから渡されたトークンが設定値と一致するか検証します。'''
        if not token or not self.webhook_token:
            return False
        return token.strip() == self.webhook_token.strip()

    def parse_webhook_payload(self, payload: object) -> SwitchBotWebhookResult:
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
            return SwitchBotWebhookResult(
                is_valid=False,
                is_motion_detected=False,
                error='invalid payload',
            )

        if payload.get('eventType') != 'changeReport':
            return SwitchBotWebhookResult(
                is_valid=False,
                is_motion_detected=False,
                error='invalid eventType',
            )

        if payload.get('eventVersion') != '1':
            return SwitchBotWebhookResult(
                is_valid=False,
                is_motion_detected=False,
                error='invalid eventVersion',
            )

        context = payload.get('context')
        if not isinstance(context, dict):
            return SwitchBotWebhookResult(
                is_valid=False,
                is_motion_detected=False,
                error='missing context',
            )

        device_type = context.get('deviceType')
        detection_state = context.get('detectionState')
        if device_type is None or detection_state is None:
            return SwitchBotWebhookResult(
                is_valid=False,
                is_motion_detected=False,
                device_type=device_type,
                detection_state=detection_state,
                error='missing context fields',
            )

        is_motion_detected = (
            device_type == 'WoPresence' and detection_state == 'DETECTED'
        )

        return SwitchBotWebhookResult(
            is_valid=True,
            is_motion_detected=is_motion_detected,
            device_type=device_type,
            detection_state=detection_state,
        )
