'''HomeIotManager - 設定クラス単体テスト
'''

import os
import unittest
from unittest.mock import patch

from homeiot import constants
from homeiot.config import Config


class TestConfig(unittest.TestCase):
    '''Config クラスのテスト'''

    def test_default_config(self):
        '''環境変数が設定されていない場合のデフォルト値検証'''
        with patch.dict(os.environ, {}, clear=True):
            config = Config.from_env()
            self.assertEqual(config.db_host, 'localhost')
            self.assertEqual(config.db_port, constants.DB_PORT)
            self.assertEqual(config.db_user, '')
            self.assertEqual(config.db_pass, '')
            self.assertEqual(config.db_name, '')
            self.assertEqual(config.target_phone_ips, [])
            self.assertEqual(config.hue_bridge_ip, '')
            self.assertEqual(config.hue_api_user, '')
            self.assertEqual(config.hue_on_scene_id, '')
            self.assertEqual(config.ifttt_webhook_key, '')
            self.assertEqual(config.switchbot_webhook_token, '')
            self.assertIsNone(config.podman_user)

    def test_from_env_custom_values(self):
        '''環境変数が設定されている場合の読み込み検証'''
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
            'PODMAN_USER': 'poduser',
        }
        with patch.dict(os.environ, env, clear=True):
            config = Config.from_env(validate=True)
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
            self.assertEqual(config.podman_user, 'poduser')

    def test_invalid_db_port_fallback(self):
        '''不正な DB_PORT の場合にデフォルト値へフォールバックされることの検証'''
        env = {'DB_PORT': 'invalid_port'}
        with patch.dict(os.environ, env, clear=True):
            config = Config.from_env()
            self.assertEqual(config.db_port, constants.DB_PORT)

    def test_validate_missing_variables(self):
        '''必須の環境変数が不足している場合に ValueError が発生することの検証'''
        config = Config()
        with self.assertRaises(ValueError) as cm:
            config.validate()
        self.assertIn('Missing required environment variables', str(cm.exception))


if __name__ == '__main__':
    unittest.main()
