'''HomeIotManager - 常駐バッチワーカー モジュール

10秒間隔で在宅・外出状況の監視および関連アクチュエータ（Hue/IFTTT/DB）制御を実行します。
'''

import logging
import signal
import time
from typing import Optional

from homeiot import constants
from homeiot.clients.hue import HueClient
from homeiot.clients.ifttt import IftttClient
from homeiot.config import Config
from homeiot.db.connector import DBConnector
from homeiot.services.home_service import HomeService

logger = logging.getLogger(__name__)


class BatchWorker:
    '''常駐監視バッチワーカー'''

    def __init__(
        self,
        config: Optional[Config] = None,
        db_connector: Optional[DBConnector] = None,
        home_service: Optional[HomeService] = None,
        interval: int = constants.CHECK_INTERVAL_SECONDS,
    ):
        if config is None:
            config = Config()

        if db_connector is None:
            db_connector = DBConnector(config)

        if home_service is None:
            hue_client = HueClient(config)
            ifttt_client = IftttClient(config)
            home_service = HomeService(
                config=config,
                db_connector=db_connector,
                hue_client=hue_client,
                ifttt_client=ifttt_client,
            )

        self.config = config
        self.db = db_connector
        self.home_service = home_service
        self.interval = interval
        self.running = False

    def stop(self, *args, **kwargs) -> None:
        '''ワーカーのループを停止します。'''
        logger.info('Stopping BatchWorker...')
        self.running = False

    def _setup_signal_handlers(self) -> None:
        '''SIGINT / SIGTERM のシグナルハンドラを設定します。'''
        try:
            signal.signal(signal.SIGINT, self.stop)
            signal.signal(signal.SIGTERM, self.stop)
        except (ValueError, AttributeError):
            logger.warning('Could not register signal handlers.')

    def run_once(self) -> None:
        '''1サイクル分の監視・処理を実行します。'''
        try:
            self.home_service.handle_presence_check()
        except Exception:
            logger.exception('Error occurred during presence check iteration.')

    def run(self) -> None:
        '''常駐監視ループを開始します。'''
        logger.info('Starting BatchWorker loop (interval: %d s)...', self.interval)
        self.running = True
        self._setup_signal_handlers()

        while self.running:
            start_time = time.time()
            self.run_once()
            elapsed = time.time() - start_time
            sleep_time = max(0.0, self.interval - elapsed)

            sleep_end = time.time() + sleep_time
            while self.running and time.time() < sleep_end:
                time.sleep(min(0.5, max(0.0, sleep_end - time.time())))

        logger.info('BatchWorker loop stopped cleanly.')


def run_worker() -> None:
    '''バッチワーカーの簡易起動ヘルパー'''
    worker = BatchWorker()
    worker.run()
