'''HomeIotManager - ICMP Ping クライアントモジュール

宅内 LAN 上のスマートフォン等の疎通確認を非同期で行います。
'''

import asyncio
import subprocess
from typing import List


async def ping_ip(ip: str) -> bool:
    '''指定された IP アドレスに ping を1回送信し、応答があるか非同期で確認します。'''
    if not ip or not ip.strip():
        return False
    try:
        proc = await asyncio.create_subprocess_exec(
            'ping',
            '-c',
            '1',
            '-w',
            '1',
            ip.strip(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        returncode = await proc.wait()
        return returncode == 0
    except Exception:
        return False


async def is_any_phone_reachable(ip_list: List[str]) -> bool:
    '''リスト内の IP アドレスに対する ping を非同期で並列送信し、1台でも応答があれば True を返します。'''
    if not ip_list:
        return False
    results = await asyncio.gather(*(ping_ip(ip) for ip in ip_list))
    return any(results)
