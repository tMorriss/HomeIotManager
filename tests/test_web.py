'''HomeIotManager - Web 層 単体テスト'''

import unittest
from unittest.mock import MagicMock, patch

from flask import Flask

from homeiot.app import create_app
from homeiot.config import Config


class TestWebApp(unittest.TestCase):
    '''Web サーバー・エンドポイントの単体テスト'''

    def setUp(self):
        self.mock_config = MagicMock(spec=Config)
        self.mock_config.switchbot_webhook_token = 'secret_token'
        self.mock_db = MagicMock()
        self.mock_switchbot_client = MagicMock()
        self.mock_home_service = MagicMock()

        self.app = create_app(
            config=self.mock_config,
            db_connector=self.mock_db,
            switchbot_client=self.mock_switchbot_client,
            home_service=self.mock_home_service,
        )
        self.client = self.app.test_client()

    def test_healthz_endpoint(self):
        '''GET /healthz の応答確認'''
        response = self.client.get('/healthz')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': 'ok'})

    def test_switchbot_webhook_unauthorized_missing_token(self):
        '''トークンなしで POST /switchbot/all を呼び出した場合 401 になるか'''
        self.mock_switchbot_client.verify_token.return_value = False

        response = self.client.post('/switchbot/all')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {'message': 'Unauthorized'})
        self.mock_switchbot_client.verify_token.assert_called_with(None)

    def test_switchbot_webhook_unauthorized_invalid_token(self):
        '''無効なトークンで POST /switchbot/all を呼び出した場合 401 になるか'''
        self.mock_switchbot_client.verify_token.return_value = False

        response = self.client.post('/switchbot/all?token=wrong_token')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {'message': 'Unauthorized'})
        self.mock_switchbot_client.verify_token.assert_called_with('wrong_token')

    def test_switchbot_webhook_success_motion_detected(self):
        '''有効なトークンかつ人感センサー検知時の正常系テスト'''
        self.mock_switchbot_client.verify_token.return_value = True
        self.mock_switchbot_client.parse_webhook_payload.return_value = {
            'is_motion_detected': True,
            'device_type': 'WoPresence',
            'detection_state': 'DETECTED',
        }
        self.mock_home_service.handle_presence_check.return_value = True

        payload = {
            'eventType': 'changeReport',
            'context': {'deviceType': 'WoPresence', 'detectionState': 'DETECTED'},
        }

        response = self.client.post('/switchbot/all?token=secret_token', json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {'status': 'ok', 'motion_detected': True, 'present': True},
        )
        self.mock_home_service.handle_presence_check.assert_called_once_with(motion_detected=True)

    def test_switchbot_webhook_success_no_motion_detected(self):
        '''有効なトークンでセンサー検知なしの場合の正常系テスト'''
        self.mock_switchbot_client.verify_token.return_value = True
        self.mock_switchbot_client.parse_webhook_payload.return_value = {
            'is_motion_detected': False,
            'device_type': 'WoPresence',
            'detection_state': 'NOT_DETECTED',
        }
        self.mock_home_service.handle_presence_check.return_value = False

        response = self.client.post('/switchbot/all?token=secret_token', json={})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {'status': 'ok', 'motion_detected': False, 'present': False},
        )
        self.mock_home_service.handle_presence_check.assert_called_once_with(motion_detected=False)

    def test_switchbot_webhook_missing_services_in_config(self):
        '''app.config 内にクライアントやサービスが存在しないエッジケース'''
        test_app = Flask(__name__)
        test_app.register_blueprint(self.app.blueprints['webhook'])
        test_client = test_app.test_client()

        response = test_client.post('/switchbot/all')
        self.assertEqual(response.status_code, 401)

    @patch('homeiot.app.HomeService')
    @patch('homeiot.app.IftttClient')
    @patch('homeiot.app.HueClient')
    @patch('homeiot.app.SwitchBotClient')
    @patch('homeiot.app.DBConnector')
    @patch('homeiot.app.Config')
    def test_create_app_defaults(
        self,
        mock_config_cls,
        mock_db_cls,
        mock_sb_cls,
        mock_hue_cls,
        mock_ifttt_cls,
        mock_hs_cls,
    ):
        '''create_app が引数なし（デフォルト）で正常に初期化されるかのテスト'''
        mock_cfg = MagicMock()
        mock_cfg.switchbot_webhook_token = 'token'
        mock_config_cls.return_value = mock_cfg

        app = create_app()

        mock_config_cls.assert_called_once()
        mock_db_cls.assert_called_once_with(mock_cfg)
        mock_sb_cls.assert_called_once_with('token')
        mock_hue_cls.assert_called_once_with(mock_cfg)
        mock_ifttt_cls.assert_called_once_with(mock_cfg)
        mock_hs_cls.assert_called_once()

        self.assertIn('APP_CONFIG', app.config)
        self.assertIn('DB_CONNECTOR', app.config)
        self.assertIn('SWITCHBOT_CLIENT', app.config)
        self.assertIn('HOME_SERVICE', app.config)


if __name__ == '__main__':
    unittest.main()
