'''HomeIotManager - ICMP Ping クライアントモジュール

宅内 LAN 上のスマートフォン等の疎通確認を行います。
'''

import subprocess
from typing import List


def ping_ip(ip: str) -> bool:
    '''指定された IP アドレスに ping を1回送信し、応答があるか確認します。'''
    if not ip or not ip.strip():
        return False
    try:
        res = subprocess.run(
            ['ping', '-c', '1', '-w', '1', ip.strip()],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return res.returncode == 0
    except Exception:
        return False


def is_any_phone_reachable(ip_list: List[str]) -> bool:
    '''リスト内の IP アドレスのうち、1台でも ping に応答があれば True を返します。'''
    for ip in ip_list:
        if ping_ip(ip):
            return True
    return False
