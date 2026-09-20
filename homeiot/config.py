'''HomeIotManager - 設定・環境変数管理モジュール

環境変数から各種接続情報・機密情報を読み込みます。
'''

import os
from dataclasses import dataclass, field
from typing import List, Optional

from homeiot import constants


@dataclass
class Config:
    '''アプリケーション設定クラス'''

    db_host: str = 'localhost'
    db_port: int = constants.DB_PORT
    db_user: str = ''
    db_pass: str = ''
    db_name: str = ''
    target_phone_ips: List[str] = field(default_factory=list)
    hue_bridge_ip: str = ''
    hue_api_user: str = ''
    hue_on_scene_id: str = ''
    ifttt_webhook_key: str = ''
    switchbot_webhook_token: str = ''
    podman_user: Optional[str] = None

    @classmethod
    def from_env(cls, validate: bool = False) -> 'Config':
        '''環境変数から Config オブジェクトを構築します。'''
        raw_ips = os.getenv('TARGET_PHONE_IPS', '')
        phone_ips = [ip.strip() for ip in raw_ips.split(',') if ip.strip()]

        try:
            db_port = int(os.getenv('DB_PORT', str(constants.DB_PORT)))
        except ValueError:
            db_port = constants.DB_PORT

        config = cls(
            db_host=os.getenv('DB_HOST', 'localhost'),
            db_port=db_port,
            db_user=os.getenv('DB_USER', ''),
            db_pass=os.getenv('DB_PASS', ''),
            db_name=os.getenv('DB_NAME', ''),
            target_phone_ips=phone_ips,
            hue_bridge_ip=os.getenv('HUE_BRIDGE_IP', ''),
            hue_api_user=os.getenv('HUE_API_USER', ''),
            hue_on_scene_id=os.getenv('HUE_ON_SCENE_ID', ''),
            ifttt_webhook_key=os.getenv('IFTTT_WEBHOOK_KEY', ''),
            switchbot_webhook_token=os.getenv('SWITCHBOT_WEBHOOK_TOKEN', ''),
            podman_user=os.getenv('PODMAN_USER'),
        )

        if validate:
            config.validate()

        return config

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
