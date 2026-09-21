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
    '''スマートホーム統括ビジネスロジックサービス'''

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

    def is_present(self, motion_detected: bool = False) -> bool:
        '''人感センサー検知またはスマホ Ping 疎通確認から在宅判定を行います。'''
        if motion_detected:
            return True
        if not self.config.target_phone_ips:
            return False
        return ping.is_any_phone_reachable(self.config.target_phone_ips)

    def is_lighting_time(self, current_time: Optional[datetime] = None) -> bool:
        '''現在時刻が自動点灯判定対象の時間帯（例: 17:00 〜 06:00）か判定します。'''
        if current_time is None:
            current_time = datetime.now()

        hour = current_time.hour
        begin = constants.HUE_ON_BEGIN_HOUR
        end = constants.HUE_ON_END_HOUR

        if begin > end:
            return hour >= begin or hour < end
        return begin <= hour < end

    def is_roomy_sleeping_time(self, current_time: Optional[datetime] = None) -> bool:
        '''現在時刻がルンバ稼働禁止時間帯（例: 22:00 〜 06:00）か判定します。'''
        if current_time is None:
            current_time = datetime.now()

        hour = current_time.hour
        start = constants.ROOMY_SLEEP_START_HOUR
        end = constants.ROOMY_SLEEP_END_HOUR

        if start > end:
            return hour >= start or hour < end
        return start <= hour < end

    def handle_presence_check(
        self, motion_detected: bool = False, current_time: Optional[datetime] = None
    ) -> bool:
        '''10秒周期または Webhook 受信時に呼び出されるメイン判定処理'''
        if current_time is None:
            current_time = datetime.now()

        present = self.is_present(motion_detected=motion_detected)
        last_in = self.db.get_last(LastName.IN)
        last_out = self.db.get_last(LastName.OUT)

        if present:
            self._handle_in_state(last_in, last_out, current_time)
        else:
            self._handle_out_state(last_in, last_out, current_time)

        return present

    def _handle_in_state(
        self,
        last_in: Optional[datetime],
        last_out: Optional[datetime],
        current_time: datetime,
    ) -> None:
        '''在宅検知時の処理'''
        self.db.set_last(LastName.IN, current_time)

        # 外出状態からの復帰（帰宅イベント）判定
        # last_out が記録されているか、または last_in が無く last_out から十分経過している場合
        is_returning = (
            last_out is not None
            and (
                last_in is None
                or last_out >= last_in
                or (current_time - last_out).total_seconds() >= constants.OUT_THRESHOLD_SECONDS
            )
        )

        if is_returning:
            logger.info('Arrival detected. Executing arrival sequence.')
            # ルンバの帰還
            self.ifttt_client.dock_roomy()

            # 照明の自動点灯
            if self.is_lighting_time(current_time):
                self.hue_client.activate_scene(
                    constants.HUE_ON_GROUP_ID, self.config.hue_on_scene_id
                )
                self.ifttt_client.turn_on_ceiling_light()

            # 入退室ログ記録
            self.db.add_in_out_log(InOutValue.IN, current_time)

    def _handle_out_state(
        self,
        last_in: Optional[datetime],
        last_out: Optional[datetime],
        current_time: datetime,
    ) -> None:
        '''不在検知時の処理'''
        if last_in is None:
            # 帰宅履歴なし、または初期状態
            return

        time_since_in = (current_time - last_in).total_seconds()

        # 外出確定判定 (しきい値 OUT_THRESHOLD_SECONDS 経過)
        if time_since_in >= constants.OUT_THRESHOLD_SECONDS:
            if last_out is None or last_out < last_in:
                logger.info('Departure confirmed. Executing departure sequence.')
                self.db.set_last(LastName.OUT, current_time)
                self.db.add_in_out_log(InOutValue.OUT, current_time)
                # 最新の last_out を更新して下続処理に引き渡す
                last_out = current_time

            # 消灯処理チェック (HUE_THRESHOLD_SECONDS 経過)
            if time_since_in >= constants.HUE_THRESHOLD_SECONDS:
                self._check_and_turn_off_lights(last_in, current_time)

            # ルンバ自動清掃開始チェック
            self._check_and_start_roomy(last_out or last_in, current_time)

    def _check_and_turn_off_lights(self, last_in: datetime, current_time: datetime) -> None:
        '''外出後の自動消灯処理'''
        # 今回の外出後にすでに消灯処理済みであれば重複実行しない
        last_hue_off = self.db.get_last(LastName.HUE_OFF)
        if last_hue_off is not None and last_hue_off >= last_in:
            return

        # Hue の点灯状態確認
        hue_is_on = True
        any_on = self.hue_client.is_any_on(constants.HUE_OFF_GROUP_ID)
        if any_on is False:
            hue_is_on = False

        if hue_is_on:
            logger.info('Turning off lights after threshold.')
            self.hue_client.turn_off_group(constants.HUE_OFF_GROUP_ID)
            self.ifttt_client.turn_off_ceiling_light()
            self.db.set_last(LastName.HUE_OFF, current_time)

    def _check_and_start_roomy(self, last_departure: datetime, current_time: datetime) -> None:
        '''外出後のルンバ自動清掃開始処理'''
        # 1. 夜間・早朝時間帯は不可
        if self.is_roomy_sleeping_time(current_time):
            return

        # 2. roomy_lock の確認 (本日以前にロックが設定されていれば実行しない)
        lock_date = self.db.get_roomy_lock()
        if lock_date is not None and lock_date >= current_time.date():
            return

        # 3. 今回の外出ですでにルンバが稼働済みであれば実行しない (1回の外出につき1回稼働)
        last_roomy = self.db.get_last(LastName.ROOMY)
        if last_roomy is not None and last_roomy >= last_departure:
            return

        logger.info('Starting Roomy cleaning sequence.')
        if self.ifttt_client.start_roomy():
            self.db.set_last(LastName.ROOMY, current_time)
