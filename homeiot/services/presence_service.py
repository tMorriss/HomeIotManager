'''HomeIotManager - 在宅判定サービスモジュール

スマホ Ping 疎通確認および人感センサー判定から在宅状態を判別します。
'''

import logging
from typing import List

from homeiot.clients import ping

logger = logging.getLogger(__name__)


class PresenceService:
    '''在宅・外出検知状態の判定サービス'''

    def __init__(self, target_phone_ips: List[str]):
        self.target_phone_ips = target_phone_ips

    def check_phone_presence(self) -> bool:
        '''ターゲット端末 (スマホ) の Ping 疎通があるか判定します。'''
        if not self.target_phone_ips:
            return False
        return ping.is_any_phone_reachable(self.target_phone_ips)

    def is_present(self, motion_detected: bool = False) -> bool:
        '''スマホ Ping 応答または人感センサー検知から在宅判定を行います。'''
        if motion_detected:
            return True
        return self.check_phone_presence()
