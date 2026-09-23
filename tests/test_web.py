'''HomeIotManager - Web 層 単体テスト'''

import pytest
from fastapi.testclient import TestClient

from homeiot.app import create_app
from homeiot.config import Config


class TestWebApp:
    '''Web サーバー・エンドポイントの単体テスト'''

    @pytest.fixture
    def app_setup(self, mocker):
        mock_config = mocker.MagicMock(spec=Config)
        mock_config.switchbot_webhook_token = 'secret_token'
        mock_db = mocker.MagicMock()
        mock_switchbot_client = mocker.MagicMock()
        mock_home_service = mocker.MagicMock()
        mock_home_service.handle_presence_check = mocker.AsyncMock()

        app = create_app(
            config=mock_config,
            db_connector=mock_db,
            switchbot_client=mock_switchbot_client,
            home_service=mock_home_service,
        )
        client = TestClient(app, raise_server_exceptions=False)
        return (
            app,
            client,
            mock_config,
            mock_db,
            mock_switchbot_client,
            mock_home_service,
        )

    def test_healthz_endpoint(self, app_setup):
        '''GET /healthz の応答確認'''
        _, client, _, _, _, _ = app_setup
        response = client.get('/healthz')
        assert response.status_code == 204
        assert response.text == ''

    def test_switchbot_webhook_unauthorized_missing_token(self, app_setup):
        '''トークンなしで POST /switchbot/all を呼び出した場合 401 になるか'''
        _, client, _, _, mock_switchbot_client, _ = app_setup
        mock_switchbot_client.verify_token.return_value = False

        response = client.post('/switchbot/all')
        assert response.status_code == 401
        assert response.json() == {'detail': {'message': 'Unauthorized'}}
        mock_switchbot_client.verify_token.assert_called_with(None)

    def test_switchbot_webhook_unauthorized_invalid_token(self, app_setup):
        '''無効なトークンで POST /switchbot/all を呼び出した場合 401 になるか'''
        _, client, _, _, mock_switchbot_client, _ = app_setup
        mock_switchbot_client.verify_token.return_value = False

        response = client.post('/switchbot/all?token=wrong_token')
        assert response.status_code == 401
        assert response.json() == {'detail': {'message': 'Unauthorized'}}
        mock_switchbot_client.verify_token.assert_called_with('wrong_token')

    def test_switchbot_webhook_success_motion_detected(self, app_setup):
        '''有効なトークンかつ人感センサー検知時の正常系テスト'''
        _, client, _, _, mock_switchbot_client, mock_home_service = app_setup
        mock_switchbot_client.verify_token.return_value = True
        mock_switchbot_client.parse_webhook_payload.return_value = {
            'is_motion_detected': True,
            'device_type': 'WoPresence',
            'detection_state': 'DETECTED',
        }
        mock_home_service.handle_presence_check.return_value = True

        payload = {
            'eventType': 'changeReport',
            'context': {'deviceType': 'WoPresence', 'detectionState': 'DETECTED'},
        }

        response = client.post('/switchbot/all?token=secret_token', json=payload)
        assert response.status_code == 204
        assert response.text == ''
        mock_home_service.handle_presence_check.assert_called_once_with(motion_detected=True)

    def test_switchbot_webhook_success_no_motion_detected(self, app_setup):
        '''有効なトークンでセンサー検知なし（Invalid JSONを含む）の場合の正常系テスト'''
        _, client, _, _, mock_switchbot_client, mock_home_service = app_setup
        mock_switchbot_client.verify_token.return_value = True
        mock_switchbot_client.parse_webhook_payload.return_value = {
            'is_motion_detected': False,
            'device_type': 'WoPresence',
            'detection_state': 'NOT_DETECTED',
        }
        mock_home_service.handle_presence_check.return_value = False

        response = client.post(
            '/switchbot/all?token=secret_token',
            content='invalid json',
            headers={'Content-Type': 'application/json'},
        )
        assert response.status_code == 204
        assert response.text == ''
        mock_home_service.handle_presence_check.assert_called_once_with(motion_detected=False)

    def test_switchbot_webhook_internal_server_error(self, app_setup):
        '''サービス処理中に例外が発生した場合に 500 エラーになるかのテスト'''
        _, client, _, _, mock_switchbot_client, mock_home_service = app_setup
        mock_switchbot_client.verify_token.return_value = True
        mock_switchbot_client.parse_webhook_payload.return_value = {
            'is_motion_detected': True,
        }
        mock_home_service.handle_presence_check.side_effect = RuntimeError('Internal error')

        response = client.post('/switchbot/all?token=secret_token', json={})
        assert response.status_code == 500
        assert response.json() == {'detail': {'message': 'Internal Server Error'}}

    def test_create_app_defaults(self, mocker):
        '''create_app が引数なし（デフォルト）で正常に初期化されるかのテスト'''
        mock_config_cls = mocker.patch('homeiot.app.Config')
        mock_db_cls = mocker.patch('homeiot.app.DBConnector')
        mock_sb_cls = mocker.patch('homeiot.app.SwitchBotClient')
        mock_hue_cls = mocker.patch('homeiot.app.HueClient')
        mock_ifttt_cls = mocker.patch('homeiot.app.IftttClient')
        mock_hs_cls = mocker.patch('homeiot.app.HomeService')

        mock_cfg = mocker.MagicMock()
        mock_cfg.switchbot_webhook_token = 'token'
        mock_cfg.hue_bridge_ip = '192.168.1.1'
        mock_cfg.hue_api_user = 'user'
        mock_cfg.ifttt_webhook_key = 'key'
        mock_config_cls.return_value = mock_cfg

        app = create_app()

        mock_config_cls.assert_called_once()
        mock_db_cls.assert_called_once_with(mock_cfg)
        mock_sb_cls.assert_called_once_with('token')
        mock_hue_cls.assert_called_once_with('192.168.1.1', 'user')
        mock_ifttt_cls.assert_called_once_with('key')
        mock_hs_cls.assert_called_once()

        assert hasattr(app.state, 'config_obj')
        assert hasattr(app.state, 'db_connector')
        assert hasattr(app.state, 'switchbot_client')
        assert hasattr(app.state, 'home_service')
