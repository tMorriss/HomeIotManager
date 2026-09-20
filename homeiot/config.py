'''HomeIotManager - 設定・環境変数管理モジュール

環境変数から各種接続情報・機密情報を読み込みます。
'''

import os
from dataclasses import dataclass
from typing import List, Optional

from homeiot import constants


@dataclass
class Config:
    '''アプリケーション設定クラス'''

    db_host: str
    db_port: int
    db_user: str
    db_pass: str
    db_name: str
    target_phone_ips: List[str]
    hue_bridge_ip: str
    hue_api_user: str
    hue_on_scene_id: str
    ifttt_webhook_key: str
    switchbot_webhook_token: str
    podman_user: Optional[str] = None

    def __init__(
        self,
        db_host: Optional[str] = None,
        db_port: Optional[int] = None,
        db_user: Optional[str] = None,
        db_pass: Optional[str] = None,
        db_name: Optional[str] = None,
        target_phone_ips: Optional[List[str]] = None,
        hue_bridge_ip: Optional[str] = None,
        hue_api_user: Optional[str] = None,
        hue_on_scene_id: Optional[str] = None,
        ifttt_webhook_key: Optional[str] = None,
        switchbot_webhook_token: Optional[str] = None,
        podman_user: Optional[str] = None,
        validate: bool = False,
    ):
        raw_ips = os.getenv('TARGET_PHONE_IPS', '')
        default_ips = [ip.strip() for ip in raw_ips.split(',') if ip.strip()]

        try:
            default_port = int(os.getenv('DB_PORT', str(constants.DB_PORT)))
        except ValueError:
            default_port = constants.DB_PORT

        self.db_host = db_host if db_host is not None else os.getenv('DB_HOST', '')
        self.db_port = db_port if db_port is not None else default_port
        self.db_user = db_user if db_user is not None else os.getenv('DB_USER', '')
        self.db_pass = db_pass if db_pass is not None else os.getenv('DB_PASS', '')
        self.db_name = db_name if db_name is not None else os.getenv('DB_NAME', '')
        self.target_phone_ips = target_phone_ips if target_phone_ips is not None else default_ips
        self.hue_bridge_ip = hue_bridge_ip if hue_bridge_ip is not None else os.getenv('HUE_BRIDGE_IP', '')
        self.hue_api_user = hue_api_user if hue_api_user is not None else os.getenv('HUE_API_USER', '')
        self.hue_on_scene_id = hue_on_scene_id if hue_on_scene_id is not None else os.getenv('HUE_ON_SCENE_ID', '')
        self.ifttt_webhook_key = ifttt_webhook_key if ifttt_webhook_key is not None else os.getenv('IFTTT_WEBHOOK_KEY', '')
        self.switchbot_webhook_token = (
            switchbot_webhook_token if switchbot_webhook_token is not None else os.getenv('SWITCHBOT_WEBHOOK_TOKEN', '')
        )
        self.podman_user = podman_user if podman_user is not None else os.getenv('PODMAN_USER')

        if validate:
            self.validate()

    def validate(self) -> None:
        '''必須設定のバリデーションを行います。'''
        required_fields = [
            ('DB_HOST', self.db_host),
            ('DB_USER', self.db_user),
            ('DB_PASS', self.db_pass),
            ('DB_NAME', self.db_name),
            ('TARGET_PHONE_IPS', self.target_phone_ips),
            ('HUE_BRIDGE_IP', self.hue_bridge_ip),
            ('HUE_API_USER', self.hue_api_user),
            ('HUE_ON_SCENE_ID', self.hue_on_scene_id),
            ('IFTTT_WEBHOOK_KEY', self.ifttt_webhook_key),
            ('SWITCHBOT_WEBHOOK_TOKEN', self.switchbot_webhook_token),
        ]
        missing = [name for name, val in required_fields if not val]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
