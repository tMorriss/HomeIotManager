'''HomeIotManager - SwitchBot クライアント / ペイロード解析モジュール

SwitchBot Cloud から受信した Webhook ペイロードの検証・解析を行います。
'''

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from homeiot.constants import JAPAN_TIMEZONE

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SwitchBotWebhookResult:
    '''SwitchBot Webhook ペイロードの解析結果'''

    device_type: str
    detection_state: str
    sample_time: Optional[datetime] = None

    @property
    def is_motion_detected(self) -> bool:
        '''従来型人感センサーの検知状態をデバイス種別と状態から求めます。'''
        return self.device_type == 'WoPresence' and self.detection_state == 'DETECTED'


class SwitchBotWebhookError(ValueError):
    '''SwitchBot Webhook ペイロードを解析できない場合の例外'''


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
        '''SwitchBot Webhook の共通形式と検知状態を解析します。

        例:
        {
            'eventType': 'changeReport',
            'eventVersion': '1',
            'context': {
                'deviceType': 'Presence Sensor',
                'detectionState': 'DETECTED',
                'timeOfSample': 1625000000000
            }
        }
        '''
        if not isinstance(payload, dict):
            raise SwitchBotWebhookError('invalid payload')

        if payload.get('eventType') != 'changeReport':
            raise SwitchBotWebhookError('invalid eventType')

        if payload.get('eventVersion') != '1':
            raise SwitchBotWebhookError('invalid eventVersion')

        context = payload.get('context')
        if not isinstance(context, dict):
            raise SwitchBotWebhookError('missing context')

        device_type = context.get('deviceType')
        detection_state = context.get('detectionState')
        if not isinstance(device_type, str) or not isinstance(detection_state, str):
            raise SwitchBotWebhookError('missing context fields')

        sample_time = None
        raw_sample_time = context.get('timeOfSample')
        if raw_sample_time is not None:
            if isinstance(raw_sample_time, bool) or not isinstance(raw_sample_time, (int, float)):
                raise SwitchBotWebhookError('invalid timeOfSample')
            try:
                sample_time = datetime.fromtimestamp(
                    raw_sample_time / 1000,
                    tz=JAPAN_TIMEZONE,
                ).replace(tzinfo=None)
            except (OverflowError, OSError, ValueError):
                raise SwitchBotWebhookError('invalid timeOfSample') from None

        return SwitchBotWebhookResult(
            device_type=device_type,
            detection_state=detection_state,
            sample_time=sample_time,
        )
