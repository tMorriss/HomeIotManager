'''HomeIotManager - 外部IoT連携クライアントの単体テスト (非同期)'''

import base64
import hashlib
import hmac
import subprocess
from types import SimpleNamespace

import httpx
import pytest

from homeiot import constants
from homeiot.clients import switchbot as switchbot_module
from homeiot.clients.hue import HueClient
from homeiot.clients.ifttt import IftttClient
from homeiot.clients.ping import is_any_phone_reachable, ping_ip
from homeiot.clients.switchbot import SwitchBotApiClient
from homeiot.clients.switchbot_webhook import SwitchBotClient, SwitchBotWebhookError


class TestPingClient:
    '''Ping クライアントのテスト'''

    @pytest.mark.asyncio
    async def test_ping_ip_success(self, mocker):
        mock_subprocess = mocker.patch('asyncio.create_subprocess_exec')
        mock_proc = mocker.MagicMock()
        mock_proc.wait = mocker.AsyncMock(return_value=0)
        mock_subprocess.return_value = mock_proc

        res = await ping_ip('192.168.1.10')
        assert res is True
        mock_subprocess.assert_called_once_with(
            'ping',
            '-c',
            '1',
            '-w',
            '1',
            '192.168.1.10',
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    @pytest.mark.asyncio
    async def test_ping_ip_failure(self, mocker):
        mock_subprocess = mocker.patch('asyncio.create_subprocess_exec')
        mock_proc = mocker.MagicMock()
        mock_proc.wait = mocker.AsyncMock(return_value=1)
        mock_subprocess.return_value = mock_proc

        res = await ping_ip('192.168.1.10')
        assert res is False

    @pytest.mark.asyncio
    async def test_ping_ip_empty(self):
        assert await ping_ip('') is False
        assert await ping_ip('   ') is False

    @pytest.mark.asyncio
    async def test_ping_ip_exception(self, mocker):
        mocker.patch('asyncio.create_subprocess_exec', side_effect=Exception('Subprocess error'))
        assert await ping_ip('192.168.1.10') is False

    @pytest.mark.asyncio
    async def test_is_any_phone_reachable(self, mocker):
        mock_ping_ip = mocker.patch('homeiot.clients.ping.ping_ip')
        mock_ping_ip.side_effect = [False, True]
        ips = ['192.168.1.10', '192.168.1.11']
        assert await is_any_phone_reachable(ips) is True

        mock_ping_ip.side_effect = [False, False]
        assert await is_any_phone_reachable(ips) is False

    @pytest.mark.asyncio
    async def test_is_any_phone_reachable_empty_list(self):
        assert await is_any_phone_reachable([]) is False


class TestHueClient:
    '''Hue クライアントのテスト'''

    @pytest.fixture
    def hue_setup(self, mocker):
        mock_async_client = mocker.MagicMock(spec=httpx.AsyncClient)
        mock_async_client.is_closed = False
        mock_async_client.aclose = mocker.AsyncMock()
        client = HueClient('192.168.1.100', 'test-user', client=mock_async_client)
        return client, mock_async_client

    @pytest.mark.asyncio
    async def test_activate_scene_success(self, hue_setup, mocker):
        client, mock_async_client = hue_setup
        mock_res = mocker.MagicMock()
        mock_res.raise_for_status.return_value = None
        mock_async_client.put = mocker.AsyncMock(return_value=mock_res)

        res = await client.activate_scene('2', 'scene-123')
        assert res is True
        mock_async_client.put.assert_called_once_with(
            'http://192.168.1.100/api/test-user/groups/2/action',
            json={'scene': 'scene-123'},
            timeout=5.0,
        )

    @pytest.mark.asyncio
    async def test_activate_scene_failure(self, hue_setup, mocker):
        client, mock_async_client = hue_setup
        mock_async_client.put = mocker.AsyncMock(side_effect=httpx.RequestError('Error'))
        res = await client.activate_scene('2', 'scene-123')
        assert res is False

    @pytest.mark.asyncio
    async def test_turn_off_group_success(self, hue_setup, mocker):
        client, mock_async_client = hue_setup
        mock_res = mocker.MagicMock()
        mock_res.raise_for_status.return_value = None
        mock_async_client.put = mocker.AsyncMock(return_value=mock_res)

        res = await client.turn_off_group('3')
        assert res is True
        mock_async_client.put.assert_called_once_with(
            'http://192.168.1.100/api/test-user/groups/3/action',
            json={'on': False},
            timeout=5.0,
        )

    @pytest.mark.asyncio
    async def test_turn_off_group_failure(self, hue_setup, mocker):
        client, mock_async_client = hue_setup
        mock_async_client.put = mocker.AsyncMock(side_effect=httpx.RequestError('Error'))
        res = await client.turn_off_group('3')
        assert res is False

    @pytest.mark.asyncio
    async def test_get_group_success(self, hue_setup, mocker):
        client, mock_async_client = hue_setup
        mock_res = mocker.MagicMock()
        mock_res.raise_for_status.return_value = None
        mock_res.json.return_value = {'action': {'on': True}}
        mock_async_client.get = mocker.AsyncMock(return_value=mock_res)

        data = await client.get_group('2')
        assert data == {'action': {'on': True}}
        mock_async_client.get.assert_called_once_with(
            'http://192.168.1.100/api/test-user/groups/2',
            timeout=5.0,
        )

    @pytest.mark.asyncio
    async def test_get_group_failure(self, hue_setup, mocker):
        client, mock_async_client = hue_setup
        mock_async_client.get = mocker.AsyncMock(side_effect=httpx.RequestError('Error'))
        data = await client.get_group('2')
        assert data is None

    @pytest.mark.asyncio
    async def test_is_any_on(self, hue_setup, mocker):
        client, _ = hue_setup
        mocker.patch.object(HueClient, 'get_group', side_effect=[
            {'state': {'any_on': True}},
            {'state': {'any_on': False}},
            {'state': {}},
            None,
        ])

        assert await client.is_any_on('2') is True
        assert await client.is_any_on('2') is False
        assert await client.is_any_on('2') is None
        assert await client.is_any_on('2') is None

    @pytest.mark.asyncio
    async def test_client_lifecycle_auto_create_and_close(self, mocker):
        mock_async_client_cls = mocker.patch('httpx.AsyncClient')
        mock_created_client = mocker.MagicMock()
        mock_created_client.is_closed = False
        mock_created_client.aclose = mocker.AsyncMock()
        mock_async_client_cls.return_value = mock_created_client

        hue = HueClient('192.168.1.100', 'test-user')
        _ = hue.client
        mock_async_client_cls.assert_called_once()

        await hue.close()
        mock_created_client.aclose.assert_called_once()


class TestIftttClient:
    '''IFTTT クライアントのテスト'''

    @pytest.fixture
    def ifttt_setup(self, mocker):
        mock_async_client = mocker.MagicMock(spec=httpx.AsyncClient)
        mock_async_client.is_closed = False
        mock_async_client.aclose = mocker.AsyncMock()
        client = IftttClient('ifttt-key-123', client=mock_async_client)
        return client, mock_async_client

    @pytest.mark.asyncio
    async def test_trigger_event_success(self, ifttt_setup, mocker):
        client, mock_async_client = ifttt_setup
        mock_res = mocker.MagicMock()
        mock_res.raise_for_status.return_value = None
        mock_async_client.get = mocker.AsyncMock(return_value=mock_res)

        res = await client.trigger_event('test_event')
        assert res is True
        mock_async_client.get.assert_called_once_with(
            'https://maker.ifttt.com/trigger/test_event/with/key/ifttt-key-123',
            timeout=5.0,
        )

    @pytest.mark.asyncio
    async def test_trigger_event_empty(self, ifttt_setup):
        client, _ = ifttt_setup
        assert await client.trigger_event('') is False

    @pytest.mark.asyncio
    async def test_trigger_event_failure(self, ifttt_setup, mocker):
        client, mock_async_client = ifttt_setup
        mock_async_client.get = mocker.AsyncMock(side_effect=httpx.RequestError('Error'))
        res = await client.trigger_event('test_event')
        assert res is False

    @pytest.mark.asyncio
    async def test_convenience_methods(self, ifttt_setup, mocker):
        client, _ = ifttt_setup
        mock_trigger = mocker.patch.object(IftttClient, 'trigger_event', return_value=True)

        assert await client.start_roomy() is True
        mock_trigger.assert_called_with('start_roomy')

        assert await client.dock_roomy() is True
        mock_trigger.assert_called_with('dock_roomy')

        assert await client.turn_on_ceiling_light() is True
        mock_trigger.assert_called_with('turn_on_ceiling_light')

        assert await client.turn_off_ceiling_light() is True
        mock_trigger.assert_called_with('turn_off_ceiling_light')

    @pytest.mark.asyncio
    async def test_client_lifecycle_auto_create_and_close(self, mocker):
        mock_async_client_cls = mocker.patch('httpx.AsyncClient')
        mock_created_client = mocker.MagicMock()
        mock_created_client.is_closed = False
        mock_created_client.aclose = mocker.AsyncMock()
        mock_async_client_cls.return_value = mock_created_client

        ifttt = IftttClient('key')
        _ = ifttt.client
        mock_async_client_cls.assert_called_once()

        await ifttt.close()
        mock_created_client.aclose.assert_called_once()


class TestSwitchBotClient:
    '''SwitchBot クライアントのテスト'''

    @pytest.fixture
    def client(self):
        return SwitchBotClient('secret-token-123')

    def test_verify_token(self, client):
        assert client.verify_token('secret-token-123') is True
        assert client.verify_token(' secret-token-123  ') is True
        assert client.verify_token('invalid-token') is False
        assert client.verify_token(None) is False

    def test_verify_token_empty_config(self):
        empty_client = SwitchBotClient('')
        assert empty_client.verify_token('secret-token-123') is False

    def test_parse_webhook_payload_valid_presence(self, client):
        payload = {
            'eventType': 'changeReport',
            'eventVersion': '1',
            'context': {
                'deviceType': 'WoPresence',
                'detectionState': 'DETECTED',
            },
        }
        res = client.parse_webhook_payload(payload)
        assert res.is_motion_detected is True
        assert res.device_type == 'WoPresence'
        assert res.detection_state == 'DETECTED'

    def test_parse_webhook_payload_other_device(self, client):
        payload = {
            'eventType': 'changeReport',
            'eventVersion': '1',
            'context': {
                'deviceType': 'WoContact',
                'detectionState': 'DETECTED',
            },
        }
        res = client.parse_webhook_payload(payload)
        assert res.is_motion_detected is False
        assert res.device_type == 'WoContact'

    def test_parse_webhook_payload_presence_sensor_pro_with_sample_time(self, client):
        payload = {
            'eventType': 'changeReport',
            'eventVersion': '1',
            'context': {
                'deviceType': 'Presence Sensor',
                'detectionState': 'NOT_DETECTED',
                'timeOfSample': 1794114741040,
            },
        }

        res = client.parse_webhook_payload(payload)

        assert res.device_type == 'Presence Sensor'
        assert res.detection_state == 'NOT_DETECTED'
        assert res.sample_time.isoformat() == '2026-11-08T14:12:21.040000'

    def test_parse_webhook_payload_rejects_invalid_sample_time(self, client):
        payload = {
            'eventType': 'changeReport',
            'eventVersion': '1',
            'context': {
                'deviceType': 'Presence Sensor',
                'detectionState': 'DETECTED',
                'timeOfSample': 'not-a-timestamp',
            },
        }

        with pytest.raises(SwitchBotWebhookError, match='invalid timeOfSample'):
            client.parse_webhook_payload(payload)

    def test_parse_webhook_payload_invalid_structure(self, client):
        with pytest.raises(SwitchBotWebhookError, match='invalid payload'):
            client.parse_webhook_payload('not a dict')

        with pytest.raises(SwitchBotWebhookError, match='missing context'):
            client.parse_webhook_payload({
                'eventType': 'changeReport',
                'eventVersion': '1',
                'context': 'not a dict',
            })

        with pytest.raises(SwitchBotWebhookError, match='missing context fields'):
            client.parse_webhook_payload({
                'eventType': 'changeReport',
                'eventVersion': '1',
                'context': {'deviceType': 'WoPresence'},
            })

    def test_parse_webhook_payload_rejects_unexpected_type_and_version(self, client):
        payload = {
            'eventType': 'changeReport',
            'eventVersion': '1',
            'context': {'deviceType': 'WoPresence', 'detectionState': 'DETECTED'},
        }

        wrong_type = {**payload, 'eventType': 'wrong'}
        wrong_version = {**payload, 'eventVersion': '1.0'}

        with pytest.raises(SwitchBotWebhookError, match='invalid eventType'):
            client.parse_webhook_payload(wrong_type)
        with pytest.raises(SwitchBotWebhookError, match='invalid eventVersion'):
            client.parse_webhook_payload(wrong_version)


class TestSwitchBotApiClient:
    '''SwitchBot OpenAPI クライアントのテスト'''

    @pytest.fixture
    def api_client(self, mocker):
        http_client = mocker.MagicMock(spec=httpx.AsyncClient)
        http_client.is_closed = False
        http_client.aclose = mocker.AsyncMock()
        http_client.request = mocker.AsyncMock()
        return SwitchBotApiClient('api-token', 'api-secret', client=http_client), http_client

    def test_auth_headers_sign_token_timestamp_and_nonce(self, monkeypatch):
        monkeypatch.setattr(switchbot_module, 'time', SimpleNamespace(time=lambda: 1.234))
        monkeypatch.setattr(switchbot_module, 'uuid', SimpleNamespace(uuid4=lambda: 'fixed-nonce'))
        client = SwitchBotApiClient('api-token', 'api-secret')

        headers = client._auth_headers()

        message = b'api-token1234fixed-nonce'
        digest = hmac.new(b'api-secret', message, hashlib.sha256).digest()
        assert headers == {
            'Authorization': 'api-token',
            'sign': base64.b64encode(digest).decode('utf-8'),
            't': '1234',
            'nonce': 'fixed-nonce',
        }

    @pytest.mark.asyncio
    async def test_request_formats_device_path_and_uses_http_method(self, mocker):
        class MockResponse:
            status_code = 200

            def raise_for_status(self):
                return None

        class MockAsyncClient:
            is_closed = False

            async def request(self, method, url, **kwargs):
                self.request_args = (method, url, kwargs)
                return MockResponse()

        http_client = MockAsyncClient()
        client = SwitchBotApiClient('api-token', 'api-secret', client=http_client)
        mocker.patch.object(client, '_auth_headers', return_value={'Authorization': 'api-token'})

        response = await client.request(
            'POST',
            '/v1.1/devices/device-123/commands',
            headers={'X-Test': 'value'},
            json={'command': 'turnOn'},
        )

        assert response.status_code == 200
        method, url, kwargs = http_client.request_args
        assert method == 'POST'
        assert url == f'{constants.SWITCHBOT_API_BASE_URL}/v1.1/devices/device-123/commands'
        assert kwargs == {
            'timeout': constants.SWITCHBOT_API_TIMEOUT_SECONDS,
            'headers': {'X-Test': 'value', 'Authorization': 'api-token'},
            'json': {'command': 'turnOn'},
        }

    @pytest.mark.asyncio
    @pytest.mark.parametrize(('status_code', 'is_active'), [(100, True), (190, False), (None, False)])
    async def test_is_active_checks_api_status_code(self, api_client, mocker, status_code, is_active):
        client, _ = api_client
        response = mocker.MagicMock()
        response.json.return_value = {'statusCode': status_code}
        mock_request = mocker.patch.object(client, 'request', new_callable=mocker.AsyncMock)
        mock_request.return_value = response

        result = await client.is_active('sensor-123')

        assert result is is_active
        mock_request.assert_awaited_once_with(
            method='GET',
            path='/v1.1/devices/sensor-123/status',
        )

    @pytest.mark.asyncio
    async def test_is_active_returns_false_when_request_fails(self, api_client, mocker):
        client, _ = api_client
        mocker.patch.object(
            client,
            'request',
            new_callable=mocker.AsyncMock,
            side_effect=httpx.RequestError('network error'),
        )

        assert await client.is_active('sensor-123') is False

    @pytest.mark.asyncio
    async def test_is_active_returns_false_for_invalid_json(self, api_client, mocker):
        client, _ = api_client
        response = mocker.MagicMock()
        response.json.side_effect = ValueError('invalid JSON')
        mocker.patch.object(
            client,
            'request',
            new_callable=mocker.AsyncMock,
            return_value=response,
        )

        assert await client.is_active('sensor-123') is False
