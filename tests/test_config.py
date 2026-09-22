'''HomeIotManager - 設定クラス単体テスト'''

import os

import pytest

from homeiot import constants
from homeiot.config import Config


class TestConfig:
    '''Config クラスのテスト'''

    def test_constants_defined(self):
        '''constants モジュールに定数が正しく定義されていることの検証'''
        assert constants.CHECK_INTERVAL_SECONDS == 10
        assert constants.OUT_THRESHOLD_SECONDS == 300
        assert constants.HUE_THRESHOLD_SECONDS == 600
        assert constants.LAST_IN_THRESHOLD_SECONDS == 180
        assert constants.HUE_ON_BEGIN_HOUR == 17
        assert constants.HUE_ON_END_HOUR == 6
        assert constants.ROOMY_SLEEP_START_HOUR == 22
        assert constants.ROOMY_SLEEP_END_HOUR == 6
        assert constants.HUE_ON_GROUP_ID == '2'
        assert constants.HUE_OFF_GROUP_ID == '3'
        assert constants.WEB_PORT == 8930

    def test_from_env_valid_values(self, monkeypatch):
        '''全環境変数が設定されている場合の正常読み込み検証'''
        env = {
            'DB_HOST': 'db.example.com',
            'DB_PORT': '3307',
            'DB_USER': 'testuser',
            'DB_PASS': 'testpass',
            'DB_NAME': 'testdb',
            'TARGET_PHONE_IPS': ' 192.168.1.10 , 192.168.1.11 ',
            'HUE_BRIDGE_IP': '192.168.1.20',
            'HUE_API_USER': 'hueuser',
            'HUE_ON_SCENE_ID': 'scene123',
            'IFTTT_WEBHOOK_KEY': 'iftttkey',
            'SWITCHBOT_WEBHOOK_TOKEN': 'swtoken',
        }
        monkeypatch.setattr(os, 'environ', env)
        config = Config()
        assert config.db_host == 'db.example.com'
        assert config.db_port == 3307
        assert config.db_user == 'testuser'
        assert config.db_pass == 'testpass'
        assert config.db_name == 'testdb'
        assert config.target_phone_ips == ['192.168.1.10', '192.168.1.11']
        assert config.hue_bridge_ip == '192.168.1.20'
        assert config.hue_api_user == 'hueuser'
        assert config.hue_on_scene_id == 'scene123'
        assert config.ifttt_webhook_key == 'iftttkey'
        assert config.switchbot_webhook_token == 'swtoken'

    def test_invalid_db_port_raises_error(self, monkeypatch):
        '''不正な DB_PORT の場合に ValueError が発生することの検証'''
        env = {
            'DB_HOST': 'db.example.com',
            'DB_PORT': 'invalid_port',
            'DB_USER': 'testuser',
            'DB_PASS': 'testpass',
            'DB_NAME': 'testdb',
            'TARGET_PHONE_IPS': '192.168.1.10',
            'HUE_BRIDGE_IP': '192.168.1.20',
            'HUE_API_USER': 'hueuser',
            'HUE_ON_SCENE_ID': 'scene123',
            'IFTTT_WEBHOOK_KEY': 'iftttkey',
            'SWITCHBOT_WEBHOOK_TOKEN': 'swtoken',
        }
        monkeypatch.setattr(os, 'environ', env)
        with pytest.raises(ValueError):
            Config()

    def test_validate_missing_variables(self, monkeypatch):
        '''必須の環境変数が不足している場合に ValueError が発生することの検証'''
        monkeypatch.setattr(os, 'environ', {})
        with pytest.raises(ValueError, match='Missing required environment variables'):
            Config()
