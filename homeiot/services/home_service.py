'''HomeIotManager - コアビジネスロジック統合サービスモジュール

在宅・外出イベントの処理、家電（Hue、IFTTT）制御、および DB（lasts, in_out）更新を行います。
'''

import logging
from datetime import datetime
from typing import Optional

from homeiot import constants
from homeiot.clients import ping
from homeiot.clients.hue import HueClient
from homeiot.clients.ifttt import IftttClient
from homeiot.config import Config
from homeiot.db.connector import DBConnector, InOutValue, LastName

logger = logging.getLogger(__name__)


class HomeService:
    '''スマートホーム統括ビジネスロジックサービス (非同期)'''

    def __init__(
        self,
        config: Config,
        db_connector: DBConnector,
        hue_client: HueClient,
        ifttt_client: IftttClient,
    ):
        self.config = config
        self.db = db_connector
        self.hue_client = hue_client
        self.ifttt_client = ifttt_client

    async def is_present(self, motion_detected: bool = False) -> bool:
        '''人感センサー検知またはスマホ Ping 疎通確認から在宅判定を行います。'''
        if motion_detected:
            return True
        if not self.config.target_phone_ips:
            return False
        return await ping.is_any_phone_reachable(self.config.target_phone_ips)

    def is_lighting_time(self, current_time: Optional[datetime] = None) -> bool:
        '''現在時刻が自動点灯判定対象の時間帯（例: 17:00 〜 06:00）か判定します。'''
        if current_time is None:
            current_time = datetime.now()

        hour = current_time.hour
        begin = constants.HUE_ON_BEGIN_HOUR
        end = constants.HUE_ON_END_HOUR

        if begin > end:
            return hour >= begin or hour <= end
        return begin <= hour < end

    def is_roomy_sleeping_time(self, current_time: Optional[datetime] = None) -> bool:
        '''現在時刻がルンバ稼働禁止時間帯（例: 22:00 〜 06:00）か判定します。'''
        if current_time is None:
            current_time = datetime.now()

        hour = current_time.hour
        start = constants.ROOMY_SLEEP_START_HOUR
        end = constants.ROOMY_SLEEP_END_HOUR

        if start > end:
            return hour >= start or hour <= end
        return start <= hour < end

    async def handle_presence_check(
        self, motion_detected: bool = False, current_time: Optional[datetime] = None
    ) -> bool:
        '''10秒周期または Webhook 受信時に呼び出されるメイン判定処理'''
        if current_time is None:
            current_time = datetime.now()

        present = await self.is_present(motion_detected=motion_detected)
        last_in = await self.db.get_last(LastName.IN)
        last_out = await self.db.get_last(LastName.OUT)
        last_hue_off = await self.db.get_last(LastName.HUE_OFF)

        if present:
            await self._handle_in_state(last_in, current_time)
        else:
            await self._handle_out_state(last_in, last_out, last_hue_off, current_time)

        await self._record_hue_off_if_lights_are_off(current_time)

        return present

    async def _handle_in_state(
        self,
        last_in: Optional[datetime],
        current_time: datetime,
    ) -> None:
        '''在宅検知時の処理'''
        # 最終在宅記録から OUT_THRESHOLD_SECONDS 以上経過していれば帰宅と判定する。
        # `out` は帰宅時刻を表し、帰宅判定は最終在宅記録時刻を基準にする。
        is_returning = (
            last_in is not None
            and (current_time - last_in).total_seconds() >= constants.OUT_THRESHOLD_SECONDS
        )

        if is_returning:
            logger.info('Arrival detected. Executing arrival sequence.')

            # 外出ログは直前の在宅時刻、帰宅ログは検知時刻で記録する。
            await self.db.add_in_out_log(InOutValue.OUT, last_in)
            await self.db.set_last(LastName.OUT, current_time)

            # ルンバの帰還
            await self.ifttt_client.dock_roomy()

            # 照明の自動点灯
            if self.is_lighting_time(current_time):
                await self.hue_client.activate_scene(
                    constants.HUE_ON_GROUP_ID, self.config.hue_on_scene_id
                )
                await self.ifttt_client.turn_on_ceiling_light()

            # 帰宅ログ記録
            await self.db.add_in_out_log(InOutValue.IN, current_time)

        # 在宅中は毎回、最終在宅時刻を更新する。
        await self.db.set_last(LastName.IN, current_time)

    async def _handle_out_state(
        self,
        last_in: Optional[datetime],
        last_out: Optional[datetime],
        last_hue_off: Optional[datetime],
        current_time: datetime,
    ) -> None:
        '''不在検知時の処理'''
        # 在宅記録がない場合は今回時刻を基準にし、外出を確定しない。
        effective_last_in = last_in or current_time
        time_since_in = (current_time - effective_last_in).total_seconds()

        # 帰宅直後の猶予中はPingが途絶えても在宅時刻を延長する。
        # 帰宅記録がない場合は猶予時間内として扱う。
        time_since_out = (
            (current_time - last_out).total_seconds()
            if last_out is not None
            else constants.LAST_IN_THRESHOLD_SECONDS
        )
        if time_since_out <= constants.LAST_IN_THRESHOLD_SECONDS:
            await self.db.set_last(LastName.IN, current_time)
            return

        # 外出確定判定 (しきい値 OUT_THRESHOLD_SECONDS 経過)
        if time_since_in >= constants.OUT_THRESHOLD_SECONDS:
            logger.info('Departure confirmed. Executing departure sequence.')

            # 最後に消灯を観測した時刻からの経過時間で消灯を判定する。
            await self._check_and_turn_off_lights(last_hue_off, current_time)

            # ルンバ自動清掃開始チェック
            await self._check_and_start_roomy(effective_last_in, current_time)

    async def _check_and_turn_off_lights(
        self, last_hue_off: Optional[datetime], current_time: datetime
    ) -> None:
        '''外出後の自動消灯処理'''
        if (
            last_hue_off is None
            or (current_time - last_hue_off).total_seconds() < constants.HUE_THRESHOLD_SECONDS
        ):
            return

        logger.info('Turning off lights after threshold.')
        await self.hue_client.turn_off_group(constants.HUE_OFF_GROUP_ID)
        await self.ifttt_client.turn_off_ceiling_light()

    async def _record_hue_off_if_lights_are_off(self, current_time: datetime) -> None:
        '''グループ2が消灯状態の場合、消灯確認時刻 `hue_off` を更新します。'''
        hue_is_on = await self.hue_client.is_any_on(constants.HUE_ON_GROUP_ID)
        if not hue_is_on:
            await self.db.set_last(LastName.HUE_OFF, current_time)

    async def _check_and_start_roomy(
        self, last_in: datetime, current_time: datetime
    ) -> None:
        '''外出後のルンバ自動清掃開始処理'''
        # 1. 夜間・早朝時間帯は不可
        if self.is_roomy_sleeping_time(current_time):
            return

        # 2. roomy_lock の確認 (本日以前にロックが設定されていれば実行しない)
        lock_date = await self.db.get_roomy_lock()
        if lock_date is not None and lock_date >= current_time.date():
            return

        # 3. 今回の外出ですでにルンバが稼働済みであれば実行しない (1回の外出につき1回稼働)
        last_roomy = await self.db.get_last(LastName.ROOMY)
        if last_roomy is not None and last_roomy >= last_in:
            return

        logger.info('Starting Roomy cleaning sequence.')
        await self.ifttt_client.start_roomy()
        # 起動要求を送信した時刻を記録し、同じ外出中の重複起動を防ぐ。
        await self.db.set_last(LastName.ROOMY, current_time)
