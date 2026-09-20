'''HomeIotManager - 設定クラス単体テスト
'''

import os
import unittest
from unittest.mock import patch

from homeiot import constants
from homeiot.config import Config


class TestConfig(unittest.TestCase):
    '''Config クラスのテスト'''

    def test_constants_defined(self):
        '''constants モジュールに定数が正しく定義されていることの検証'''
        self.assertEqual(constants.CHECK_INTERVAL_SECONDS, 10)
        self.assertEqual(constants.OUT_THRESHOLD_SECONDS, 300)
        self.assertEqual(constants.HUE_THRESHOLD_SECONDS, 600)
        self.assertEqual(constants.LAST_IN_THRESHOLD_SECONDS, 180)
        self.assertEqual(constants.HUE_ON_BEGIN_HOUR, 17)
        self.assertEqual(constants.HUE_ON_END_HOUR, 6)
        self.assertEqual(constants.ROOMY_SLEEP_START_HOUR, 22)
        self.assertEqual(constants.ROOMY_SLEEP_END_HOUR, 6)
        self.assertEqual(constants.HUE_ON_GROUP_ID, '2')
        self.assertEqual(constants.HUE_OFF_GROUP_ID, '3')
        self.assertEqual(constants.WEB_PORT, 8930)

    def test_from_env_valid_values(self):
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
        with patch.dict(os.environ, env, clear=True):
            config = Config()
            self.assertEqual(config.db_host, 'db.example.com')
            self.assertEqual(config.db_port, 3307)
            self.assertEqual(config.db_user, 'testuser')
            self.assertEqual(config.db_pass, 'testpass')
            self.assertEqual(config.db_name, 'testdb')
            self.assertEqual(config.target_phone_ips, ['192.168.1.10', '192.168.1.11'])
            self.assertEqual(config.hue_bridge_ip, '192.168.1.20')
            self.assertEqual(config.hue_api_user, 'hueuser')
            self.assertEqual(config.hue_on_scene_id, 'scene123')
            self.assertEqual(config.ifttt_webhook_key, 'iftttkey')
            self.assertEqual(config.switchbot_webhook_token, 'swtoken')

    def test_invalid_db_port_raises_error(self):
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
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ValueError) as cm:
                Config()
            self.assertIn('DB_PORT', str(cm.exception))

    def test_validate_missing_variables(self):
        '''必須の環境変数が不足している場合に ValueError が発生することの検証'''
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as cm:
                Config()
            self.assertIn('Missing required environment variables', str(cm.exception))


if __name__ == '__main__':
    unittest.main()
