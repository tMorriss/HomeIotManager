'''HomeIotManager - 外部IoT連携クライアントの単体テスト'''

import subprocess
import unittest
from unittest.mock import MagicMock, patch

import requests

from homeiot.clients.hue import HueClient
from homeiot.clients.ifttt import IftttClient
from homeiot.clients.ping import is_any_phone_reachable, ping_ip
from homeiot.clients.switchbot import SwitchBotClient


class TestPingClient(unittest.TestCase):
    '''Ping クライアントのテスト'''

    @patch('subprocess.run')
    def test_ping_ip_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        self.assertTrue(ping_ip('192.168.1.10'))
        mock_run.assert_called_once_with(
            ['ping', '-c', '1', '-w', '1', '192.168.1.10'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    @patch('subprocess.run')
    def test_ping_ip_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        self.assertFalse(ping_ip('192.168.1.10'))

    def test_ping_ip_empty(self):
        self.assertFalse(ping_ip(''))
        self.assertFalse(ping_ip('   '))

    @patch('subprocess.run', side_effect=Exception('Subprocess error'))
    def test_ping_ip_exception(self, mock_run):
        self.assertFalse(ping_ip('192.168.1.10'))

    @patch('homeiot.clients.ping.ping_ip')
    def test_is_any_phone_reachable(self, mock_ping_ip):
        mock_ping_ip.side_effect = [False, True]
        ips = ['192.168.1.10', '192.168.1.11']
        self.assertTrue(is_any_phone_reachable(ips))

        mock_ping_ip.side_effect = [False, False]
        self.assertFalse(is_any_phone_reachable(ips))


class TestHueClient(unittest.TestCase):
    '''Hue クライアントのテスト'''

    def setUp(self):
        self.mock_session = MagicMock(spec=requests.Session)
        self.client = HueClient('192.168.1.100', 'test-user', session=self.mock_session)

    def test_activate_scene_success(self):
        mock_res = MagicMock()
        mock_res.raise_for_status.return_value = None
        self.mock_session.put.return_value = mock_res

        res = self.client.activate_scene('2', 'scene-123')
        self.assertTrue(res)
        self.mock_session.put.assert_called_once_with(
            'http://192.168.1.100/api/test-user/groups/2/action',
            json={'scene': 'scene-123'},
            timeout=5,
        )

    def test_activate_scene_failure(self):
        self.mock_session.put.side_effect = requests.RequestException('Error')
        res = self.client.activate_scene('2', 'scene-123')
        self.assertFalse(res)

    def test_turn_off_group_success(self):
        mock_res = MagicMock()
        mock_res.raise_for_status.return_value = None
        self.mock_session.put.return_value = mock_res

        res = self.client.turn_off_group('3')
        self.assertTrue(res)
        self.mock_session.put.assert_called_once_with(
            'http://192.168.1.100/api/test-user/groups/3/action',
            json={'on': False},
            timeout=5,
        )

    def test_turn_off_group_failure(self):
        self.mock_session.put.side_effect = requests.RequestException('Error')
        res = self.client.turn_off_group('3')
        self.assertFalse(res)

    def test_get_group_success(self):
        mock_res = MagicMock()
        mock_res.raise_for_status.return_value = None
        mock_res.json.return_value = {'action': {'on': True}}
        self.mock_session.get.return_value = mock_res

        data = self.client.get_group('2')
        self.assertEqual(data, {'action': {'on': True}})
        self.mock_session.get.assert_called_once_with(
            'http://192.168.1.100/api/test-user/groups/2',
            timeout=5,
        )

    def test_get_group_failure(self):
        self.mock_session.get.side_effect = requests.RequestException('Error')
        data = self.client.get_group('2')
        self.assertIsNone(data)


class TestIftttClient(unittest.TestCase):
    '''IFTTT クライアントのテスト'''

    def setUp(self):
        self.mock_session = MagicMock(spec=requests.Session)
        self.client = IftttClient('ifttt-key-123', session=self.mock_session)

    def test_trigger_event_success(self):
        mock_res = MagicMock()
        mock_res.raise_for_status.return_value = None
        self.mock_session.post.return_value = mock_res

        res = self.client.trigger_event('test_event')
        self.assertTrue(res)
        self.mock_session.post.assert_called_once_with(
            'https://maker.ifttt.com/trigger/test_event/with/key/ifttt-key-123',
            timeout=5,
        )

    def test_trigger_event_empty(self):
        self.assertFalse(self.client.trigger_event(''))

    def test_trigger_event_failure(self):
        self.mock_session.post.side_effect = requests.RequestException('Error')
        res = self.client.trigger_event('test_event')
        self.assertFalse(res)

    @patch.object(IftttClient, 'trigger_event')
    def test_convenience_methods(self, mock_trigger):
        mock_trigger.return_value = True

        self.assertTrue(self.client.start_roomy())
        mock_trigger.assert_called_with('start_roomy')

        self.assertTrue(self.client.dock_roomy())
        mock_trigger.assert_called_with('dock_roomy')

        self.assertTrue(self.client.turn_on_ceiling_light())
        mock_trigger.assert_called_with('turn_on_ceiling_light')

        self.assertTrue(self.client.turn_off_ceiling_light())
        mock_trigger.assert_called_with('turn_off_ceiling_light')


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
