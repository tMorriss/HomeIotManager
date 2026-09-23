'''HomeIotManager - 非同期バッチワーカー モジュール

定期的に在宅状況判定ロジックを実行する常駐型バッチワーカーです。
'''

import asyncio
import logging
import signal
from typing import Optional

from homeiot.clients.hue import HueClient
from homeiot.clients.ifttt import IftttClient
from homeiot.config import Config
from homeiot.db.connector import DBConnector
from homeiot.services.home_service import HomeService

logger = logging.getLogger(__name__)


class BatchWorker:
    '''常駐非同期バッチワーカースラス'''

    def __init__(self, home_service: Optional[HomeService] = None) -> None:
        '''BatchWorker の初期化'''
        if home_service is None:
            config = Config()
            db_connector = DBConnector(config)
            hue_client = HueClient(config.hue_bridge_ip, config.hue_api_user)
            ifttt_client = IftttClient(config.ifttt_webhook_key)
            home_service = HomeService(
                config=config,
                db_connector=db_connector,
                hue_client=hue_client,
                ifttt_client=ifttt_client,
            )

        self.home_service = home_service
        self.interval = 10
        self._running = False

    def stop(self) -> None:
        '''ワーカーのループ停止を要求します'''
        logger.info('Stopping BatchWorker...')
        self._running = False

    async def run(self) -> None:
        '''非同期バッチループを実行します'''
        self._running = True
        logger.info('BatchWorker started (interval: %d seconds).', self.interval)

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self.stop)
            except (NotImplementedError, RuntimeError):
                # Windows や特定の非メインスレッド等で add_signal_handler がサポートされていない場合のフォールバック
                pass

        while self._running:
            try:
                logger.debug('Executing periodic presence check...')
                await self.home_service.handle_presence_check()
            except Exception as e:
                logger.error('Error occurred in BatchWorker execution loop: %s', e, exc_info=True)

            try:
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                logger.info('BatchWorker sleep cancelled.')
                break

        logger.info('BatchWorker stopped.')
