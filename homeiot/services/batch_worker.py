'''HomeIotManager - 常駐非同期バッチワーカー モジュール

定期的に在宅・外出の判定およびスマート家電の制御を行う常駐バッチサービスを提供します。
'''

import asyncio
import logging
import signal
from typing import Optional

from homeiot import constants
from homeiot.clients.hue import HueClient
from homeiot.clients.ifttt import IftttClient
from homeiot.config import Config
from homeiot.db.connector import DBConnector
from homeiot.services.home_service import HomeService

logger = logging.getLogger(__name__)


class BatchWorker:
    '''常駐非同期バッチワーカー クラス'''

    def __init__(
        self,
        config: Optional[Config] = None,
        db_connector: Optional[DBConnector] = None,
        home_service: Optional[HomeService] = None,
        interval: int = constants.CHECK_INTERVAL_SECONDS,
    ):
        self.config = config or Config()
        self.db = db_connector or DBConnector(self.config)
        if home_service is None:
            hue_client = HueClient(self.config.hue_bridge_ip, self.config.hue_api_user)
            ifttt_client = IftttClient(self.config.ifttt_webhook_key)
            self.home_service = HomeService(
                config=self.config,
                db_connector=self.db,
                hue_client=hue_client,
                ifttt_client=ifttt_client,
            )
        else:
            self.home_service = home_service
        self.interval = interval
        self.running = False
        self._shutdown_event = asyncio.Event()

    async def run_once(self) -> None:
        '''1回分の在宅判定および処理を実行します。'''
        try:
            await self.home_service.handle_presence_check()
        except Exception:
            logger.exception('Error occurred during presence check')

    async def start(self) -> None:
        '''バッチワーカーの常駐ループを開始します。'''
        self.running = True
        self._shutdown_event.clear()
        self._setup_signal_handlers()
        logger.info('Batch worker started. Running every %d seconds.', self.interval)

        try:
            while self.running:
                await self.run_once()
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(), timeout=self.interval
                    )
                except asyncio.TimeoutError:
                    pass
        finally:
            await self.stop()

    def _setup_signal_handlers(self) -> None:
        '''SIGINT および SIGTERM シグナルハンドラーを登録します。'''
        try:
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, self.request_stop)
        except (NotImplementedError, RuntimeError):
            pass

    def request_stop(self) -> None:
        '''停止シグナルを受け取った際に呼び出され、ワーカー停止を要求します。'''
        logger.info('Stop request received. Shutting down batch worker...')
        self.running = False
        self._shutdown_event.set()

    async def stop(self) -> None:
        '''バッチワーカーを安全に停止し、リソースを解放します。'''
        self.running = False
        self._shutdown_event.set()
        await self.db.close()
        logger.info('Batch worker stopped.')
