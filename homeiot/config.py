'''HomeIotManager - 設定・環境変数管理モジュール

環境変数から各種接続情報・機密情報を読み込みます。
'''

import os
from typing import List


class Config:
    '''アプリケーション設定クラス'''

    def __init__(self):
        raw_ips = os.getenv('TARGET_PHONE_IPS', '')
        self.target_phone_ips: List[str] = [ip.strip() for ip in raw_ips.split(',') if ip.strip()]
        self.db_port: int = int(os.getenv('DB_PORT', 0))
        self.db_host: str = os.getenv('DB_HOST', '')
        self.db_user: str = os.getenv('DB_USER', '')
        self.db_pass: str = os.getenv('DB_PASS', '')
        self.db_name: str = os.getenv('DB_NAME', '')
        self.hue_bridge_ip: str = os.getenv('HUE_BRIDGE_IP', '')
        self.hue_api_user: str = os.getenv('HUE_API_USER', '')
        self.hue_on_scene_id: str = os.getenv('HUE_ON_SCENE_ID', '')
        self.ifttt_webhook_key: str = os.getenv('IFTTT_WEBHOOK_KEY', '')
        self.switchbot_webhook_token: str = os.getenv('SWITCHBOT_WEBHOOK_TOKEN', '')

        self.validate()

    def validate(self) -> None:
        '''必須設定のバリデーションを行います。'''
        required_fields = [
            ('DB_HOST', self.db_host),
            ('DB_PORT', self.db_port),
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
