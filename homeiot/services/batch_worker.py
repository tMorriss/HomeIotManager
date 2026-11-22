'''HomeIotManager - 常駐非同期バッチワーカー モジュール

定期的に在宅・外出の判定およびスマート家電の制御を行う常駐バッチサービスを提供します。
'''

import asyncio
import logging
import signal
from datetime import datetime
from typing import Awaitable, Callable, Optional

from homeiot import constants
from homeiot.clients.hue import HueClient
from homeiot.clients.ifttt import IftttClient
from homeiot.clients.switchbot import SwitchBotApiClient
from homeiot.config import Config
from homeiot.db.connector import DBConnector, LastName
from homeiot.services.home_service import HomeService

logger = logging.getLogger(__name__)


class BatchWorker:
    '''常駐非同期バッチワーカー クラス'''

    def __init__(
        self,
        config: Optional[Config] = None,
        db_connector: Optional[DBConnector] = None,
        home_service: Optional[HomeService] = None,
        switchbot_api_client: Optional[SwitchBotApiClient] = None,
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
        self.switchbot_api = switchbot_api_client or SwitchBotApiClient(
            self.config.switchbot_api_token,
            self.config.switchbot_api_secret,
        )
        self.running = False
        self._shutdown_event = asyncio.Event()

    async def run_presence_check_once(self) -> None:
        '''1回分の在宅判定および処理を実行します。'''
        try:
            await self.home_service.handle_presence_check()
        except Exception:
            logger.exception('Error occurred during presence check')

    async def check_presence_sensor_health(self) -> None:
        '''SwitchBot API でセンサー死活を確認し、確認日時を保存します。'''
        current_time = datetime.now()
        try:
            sensor_is_active = await self.switchbot_api.is_active(
                self.config.presence_sensor_device_id
            )
        except Exception:
            logger.exception('SwitchBot presence sensor health check failed.')
            sensor_is_active = False

        status_key = (
            LastName.PRESENCE_SENSOR_ACTIVE
            if sensor_is_active
            else LastName.PRESENCE_SENSOR_INACTIVE
        )
        await self.db.set_last(status_key, current_time)

    async def _run_periodic_loop(
        self,
        interval: int,
        operation: Callable[[], Awaitable[None]],
        loop_name: str,
    ) -> None:
        '''指定された処理を停止要求まで周期実行します。'''
        while self.running:
            try:
                await operation()
            except Exception:
                logger.exception('Error occurred in %s loop', loop_name)

            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass

    async def start(self) -> None:
        '''在室判定と死活監視の常駐ループを開始します。'''
        self.running = True
        self._shutdown_event.clear()
        self._setup_signal_handlers()
        periodic_loops = [
            (
                constants.PRESENCE_CHECK_INTERVAL_SECONDS,
                self.run_presence_check_once,
                'presence_check',
            ),
            (
                constants.PRESENCE_SENSOR_HEALTH_CHECK_INTERVAL_SECONDS,
                self.check_presence_sensor_health,
                'presence_sensor_health_check',
            ),
        ]
        loop_tasks = [
            asyncio.create_task(
                self._run_periodic_loop(interval, operation, loop_name),
                name=f'homeiot-{loop_name}-loop',
            )
            for interval, operation, loop_name in periodic_loops
        ]
        logger.info('Batch worker started with %d periodic loops.', len(loop_tasks))

        try:
            await self._shutdown_event.wait()
        finally:
            self.running = False
            for task in loop_tasks:
                task.cancel()
            await asyncio.gather(*loop_tasks, return_exceptions=True)
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
        await self.switchbot_api.close()
        logger.info('Batch worker stopped.')
