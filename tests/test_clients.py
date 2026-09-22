'''HomeIotManager - 外部IoT連携クライアントの単体テスト (非同期)'''

import subprocess

import httpx
import pytest

from homeiot.clients.hue import HueClient
from homeiot.clients.ifttt import IftttClient
from homeiot.clients.ping import is_any_phone_reachable, ping_ip
from homeiot.clients.switchbot import SwitchBotClient


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
        mock_async_client.post = mocker.AsyncMock(return_value=mock_res)

        res = await client.trigger_event('test_event')
        assert res is True
        mock_async_client.post.assert_called_once_with(
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
        mock_async_client.post = mocker.AsyncMock(side_effect=httpx.RequestError('Error'))
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
            'context': {
                'deviceType': 'WoPresence',
                'detectionState': 'DETECTED',
            },
        }
        res = client.parse_webhook_payload(payload)
        assert res['is_motion_detected'] is True
        assert res['device_type'] == 'WoPresence'
        assert res['detection_state'] == 'DETECTED'

    def test_parse_webhook_payload_other_device(self, client):
        payload = {
            'eventType': 'changeReport',
            'context': {
                'deviceType': 'WoContact',
                'detectionState': 'DETECTED',
            },
        }
        res = client.parse_webhook_payload(payload)
        assert res['is_motion_detected'] is False

    def test_parse_webhook_payload_invalid_structure(self, client):
        res = client.parse_webhook_payload('not a dict')
        assert res['is_motion_detected'] is False

        res = client.parse_webhook_payload({'context': 'not a dict'})
        assert res['is_motion_detected'] is False
