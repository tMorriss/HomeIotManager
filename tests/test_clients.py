'''HomeIotManager - 外部IoT連携クライアントの単体テスト (非同期)'''

import subprocess
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from homeiot.clients.hue import HueClient
from homeiot.clients.ifttt import IftttClient
from homeiot.clients.ping import is_any_phone_reachable, ping_ip
from homeiot.clients.switchbot import SwitchBotClient


class TestPingClient(unittest.IsolatedAsyncioTestCase):
    '''Ping クライアントのテスト'''

    @patch('asyncio.create_subprocess_exec')
    async def test_ping_ip_success(self, mock_subprocess):
        mock_proc = MagicMock()
        mock_proc.wait = AsyncMock(return_value=0)
        mock_subprocess.return_value = mock_proc

        res = await ping_ip('192.168.1.10')
        self.assertTrue(res)
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

    @patch('asyncio.create_subprocess_exec')
    async def test_ping_ip_failure(self, mock_subprocess):
        mock_proc = MagicMock()
        mock_proc.wait = AsyncMock(return_value=1)
        mock_subprocess.return_value = mock_proc

        res = await ping_ip('192.168.1.10')
        self.assertFalse(res)

    async def test_ping_ip_empty(self):
        self.assertFalse(await ping_ip(''))
        self.assertFalse(await ping_ip('   '))

    @patch('asyncio.create_subprocess_exec', side_effect=Exception('Subprocess error'))
    async def test_ping_ip_exception(self, mock_subprocess):
        self.assertFalse(await ping_ip('192.168.1.10'))

    @patch('homeiot.clients.ping.ping_ip')
    async def test_is_any_phone_reachable(self, mock_ping_ip):
        mock_ping_ip.side_effect = [False, True]
        ips = ['192.168.1.10', '192.168.1.11']
        self.assertTrue(await is_any_phone_reachable(ips))

        mock_ping_ip.side_effect = [False, False]
        self.assertFalse(await is_any_phone_reachable(ips))

    async def test_is_any_phone_reachable_empty_list(self):
        self.assertFalse(await is_any_phone_reachable([]))


class TestHueClient(unittest.IsolatedAsyncioTestCase):
    '''Hue クライアントのテスト'''

    async def asyncSetUp(self):
        self.mock_async_client = MagicMock(spec=httpx.AsyncClient)
        self.mock_async_client.is_closed = False
        self.mock_async_client.aclose = AsyncMock()
        self.client = HueClient('192.168.1.100', 'test-user', client=self.mock_async_client)

    async def asyncTearDown(self):
        await self.client.close()

    async def test_activate_scene_success(self):
        mock_res = MagicMock()
        mock_res.raise_for_status.return_value = None
        self.mock_async_client.put = AsyncMock(return_value=mock_res)

        res = await self.client.activate_scene('2', 'scene-123')
        self.assertTrue(res)
        self.mock_async_client.put.assert_called_once_with(
            'http://192.168.1.100/api/test-user/groups/2/action',
            json={'scene': 'scene-123'},
            timeout=5.0,
        )

    async def test_activate_scene_failure(self):
        self.mock_async_client.put = AsyncMock(side_effect=httpx.RequestError('Error'))
        res = await self.client.activate_scene('2', 'scene-123')
        self.assertFalse(res)

    async def test_turn_off_group_success(self):
        mock_res = MagicMock()
        mock_res.raise_for_status.return_value = None
        self.mock_async_client.put = AsyncMock(return_value=mock_res)

        res = await self.client.turn_off_group('3')
        self.assertTrue(res)
        self.mock_async_client.put.assert_called_once_with(
            'http://192.168.1.100/api/test-user/groups/3/action',
            json={'on': False},
            timeout=5.0,
        )

    async def test_turn_off_group_failure(self):
        self.mock_async_client.put = AsyncMock(side_effect=httpx.RequestError('Error'))
        res = await self.client.turn_off_group('3')
        self.assertFalse(res)

    async def test_get_group_success(self):
        mock_res = MagicMock()
        mock_res.raise_for_status.return_value = None
        mock_res.json.return_value = {'action': {'on': True}}
        self.mock_async_client.get = AsyncMock(return_value=mock_res)

        data = await self.client.get_group('2')
        self.assertEqual(data, {'action': {'on': True}})
        self.mock_async_client.get.assert_called_once_with(
            'http://192.168.1.100/api/test-user/groups/2',
            timeout=5.0,
        )

    async def test_get_group_failure(self):
        self.mock_async_client.get = AsyncMock(side_effect=httpx.RequestError('Error'))
        data = await self.client.get_group('2')
        self.assertIsNone(data)

    @patch.object(HueClient, 'get_group')
    async def test_is_any_on(self, mock_get_group):
        mock_get_group.return_value = {'state': {'any_on': True}}
        self.assertTrue(await self.client.is_any_on('2'))

        mock_get_group.return_value = {'state': {'any_on': False}}
        self.assertFalse(await self.client.is_any_on('2'))

        mock_get_group.return_value = {'state': {}}
        self.assertIsNone(await self.client.is_any_on('2'))

        mock_get_group.return_value = None
        self.assertIsNone(await self.client.is_any_on('2'))

    @patch('httpx.AsyncClient')
    async def test_client_lifecycle_auto_create_and_close(self, mock_async_client_cls):
        mock_created_client = MagicMock()
        mock_created_client.is_closed = False
        mock_created_client.aclose = AsyncMock()
        mock_async_client_cls.return_value = mock_created_client

        hue = HueClient('192.168.1.100', 'test-user')
        _ = hue.client
        mock_async_client_cls.assert_called_once()

        await hue.close()
        mock_created_client.aclose.assert_called_once()


class TestIftttClient(unittest.IsolatedAsyncioTestCase):
    '''IFTTT クライアントのテスト'''

    async def asyncSetUp(self):
        self.mock_async_client = MagicMock(spec=httpx.AsyncClient)
        self.mock_async_client.is_closed = False
        self.mock_async_client.aclose = AsyncMock()
        self.client = IftttClient('ifttt-key-123', client=self.mock_async_client)

    async def asyncTearDown(self):
        await self.client.close()

    async def test_trigger_event_success(self):
        mock_res = MagicMock()
        mock_res.raise_for_status.return_value = None
        self.mock_async_client.post = AsyncMock(return_value=mock_res)

        res = await self.client.trigger_event('test_event')
        self.assertTrue(res)
        self.mock_async_client.post.assert_called_once_with(
            'https://maker.ifttt.com/trigger/test_event/with/key/ifttt-key-123',
            timeout=5.0,
        )

    async def test_trigger_event_empty(self):
        self.assertFalse(await self.client.trigger_event(''))

    async def test_trigger_event_failure(self):
        self.mock_async_client.post = AsyncMock(side_effect=httpx.RequestError('Error'))
        res = await self.client.trigger_event('test_event')
        self.assertFalse(res)

    @patch.object(IftttClient, 'trigger_event')
    async def test_convenience_methods(self, mock_trigger):
        mock_trigger.return_value = True

        self.assertTrue(await self.client.start_roomy())
        mock_trigger.assert_called_with('start_roomy')

        self.assertTrue(await self.client.dock_roomy())
        mock_trigger.assert_called_with('dock_roomy')

        self.assertTrue(await self.client.turn_on_ceiling_light())
        mock_trigger.assert_called_with('turn_on_ceiling_light')

        self.assertTrue(await self.client.turn_off_ceiling_light())
        mock_trigger.assert_called_with('turn_off_ceiling_light')

    @patch('httpx.AsyncClient')
    async def test_client_lifecycle_auto_create_and_close(self, mock_async_client_cls):
        mock_created_client = MagicMock()
        mock_created_client.is_closed = False
        mock_created_client.aclose = AsyncMock()
        mock_async_client_cls.return_value = mock_created_client

        ifttt = IftttClient('key')
        _ = ifttt.client
        mock_async_client_cls.assert_called_once()

        await ifttt.close()
        mock_created_client.aclose.assert_called_once()


class TestSwitchBotClient(unittest.TestCase):
    '''SwitchBot クライアントのテスト'''

    def setUp(self):
        self.client = SwitchBotClient('secret-token-123')

    def test_verify_token(self):
        self.assertTrue(self.client.verify_token('secret-token-123'))
        self.assertTrue(self.client.verify_token(' secret-token-123  '))
        self.assertFalse(self.client.verify_token('invalid-token'))
        self.assertFalse(self.client.verify_token(None))

    def test_verify_token_empty_config(self):
        empty_client = SwitchBotClient('')
        self.assertFalse(empty_client.verify_token('secret-token-123'))

    def test_parse_webhook_payload_valid_presence(self):
        payload = {
            'eventType': 'changeReport',
            'context': {
                'deviceType': 'WoPresence',
                'detectionState': 'DETECTED',
            },
        }
        res = self.client.parse_webhook_payload(payload)
        self.assertTrue(res['is_motion_detected'])
        self.assertEqual(res['device_type'], 'WoPresence')
        self.assertEqual(res['detection_state'], 'DETECTED')

    def test_parse_webhook_payload_other_device(self):
        payload = {
            'eventType': 'changeReport',
            'context': {
                'deviceType': 'WoContact',
                'detectionState': 'DETECTED',
            },
        }
        res = self.client.parse_webhook_payload(payload)
        self.assertFalse(res['is_motion_detected'])

    def test_parse_webhook_payload_invalid_structure(self):
        res = self.client.parse_webhook_payload('not a dict')
        self.assertFalse(res['is_motion_detected'])

        res = self.client.parse_webhook_payload({'context': 'not a dict'})
        self.assertFalse(res['is_motion_detected'])


if __name__ == '__main__':
    unittest.main()
