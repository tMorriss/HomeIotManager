'''HomeIotManager - IFTTT Maker Webhook クライアントモジュール

IFTTT Webhook サービスを経由してスマート家電（ルンバ・シーリングライト）を非同期で制御します。
httpx.AsyncClient による非同期 HTTP リクエストとコネクション再利用に対応しています。
'''

import logging
from typing import Optional

import httpx

from homeiot.clients.base import BaseHttpClient

logger = logging.getLogger(__name__)


class IftttClient(BaseHttpClient):
    '''IFTTT Webhook クライアント (非同期)'''

    def __init__(self, webhook_key: str, client: Optional[httpx.AsyncClient] = None):
        super().__init__(client=client)
        self.webhook_key = webhook_key

    async def trigger_event(self, event_name: str) -> bool:
        '''指定されたイベント名で IFTTT Webhook を非同期呼び出しします。'''
        if not event_name:
            return False
        url = f'https://maker.ifttt.com/trigger/{event_name}/with/key/{self.webhook_key}'
        try:
            res = await self.client.post(url, timeout=5.0)
            res.raise_for_status()
            return True
        except Exception as e:
            logger.error(f'Failed to trigger IFTTT event {event_name}: {e}')
            return False

    async def start_roomy(self) -> bool:
        '''ルンバの清掃開始イベント (start_roomy) を送信します。'''
        return await self.trigger_event('start_roomy')

    async def dock_roomy(self) -> bool:
        '''ルンバのドック帰還イベント (dock_roomy) を送信します。'''
        return await self.trigger_event('dock_roomy')

    async def turn_on_ceiling_light(self) -> bool:
        '''シーリングライトの点灯イベント (turn_on_ceiling_light) を送信します。'''
        return await self.trigger_event('turn_on_ceiling_light')

    async def turn_off_ceiling_light(self) -> bool:
        '''シーリングライトの消灯イベント (turn_off_ceiling_light) を送信します。'''
        return await self.trigger_event('turn_off_ceiling_light')
