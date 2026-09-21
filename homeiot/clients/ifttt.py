'''HomeIotManager - IFTTT Maker Webhook クライアントモジュール

IFTTT Webhook サービスを経由してスマート家電（ルンバ・シーリングライト）を制御します。
常駐バッチ環境に配慮し requests.Session によるコネクション再利用に対応しています。
'''

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class IftttClient:
    '''IFTTT Webhook クライアント'''

    def __init__(self, webhook_key: str, session: Optional[requests.Session] = None):
        self.webhook_key = webhook_key
        self.session = session or requests.Session()

    def trigger_event(self, event_name: str) -> bool:
        '''指定されたイベント名で IFTTT Webhook を呼び出します。'''
        if not event_name:
            return False
        url = f'https://maker.ifttt.com/trigger/{event_name}/with/key/{self.webhook_key}'
        try:
            res = self.session.post(url, timeout=5)
            res.raise_for_status()
            return True
        except Exception as e:
            logger.error(f'Failed to trigger IFTTT event {event_name}: {e}')
            return False

    def start_roomy(self) -> bool:
        '''ルンバの清掃開始イベント (start_roomy) を送信します。'''
        return self.trigger_event('start_roomy')

    def dock_roomy(self) -> bool:
        '''ルンバのドック帰還イベント (dock_roomy) を送信します。'''
        return self.trigger_event('dock_roomy')

    def turn_on_ceiling_light(self) -> bool:
        '''シーリングライトの点灯イベント (turn_on_ceiling_light) を送信します。'''
        return self.trigger_event('turn_on_ceiling_light')

    def turn_off_ceiling_light(self) -> bool:
        '''シーリングライトの消灯イベント (turn_off_ceiling_light) を送信します。'''
        return self.trigger_event('turn_off_ceiling_light')
