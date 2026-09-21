'''HomeIotManager - サービス層単体テスト'''

import unittest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

from homeiot import constants
from homeiot.config import Config
from homeiot.db.connector import InOutValue, LastName
from homeiot.services.home_service import HomeService
from homeiot.services.presence_service import PresenceService


class TestPresenceService(unittest.TestCase):
    '''PresenceService のテスト'''

    @patch('homeiot.clients.ping.is_any_phone_reachable')
    def test_check_phone_presence(self, mock_ping):
        service = PresenceService(['192.168.1.10'])

        mock_ping.return_value = True
        self.assertTrue(service.check_phone_presence())
        mock_ping.assert_called_once_with(['192.168.1.10'])

        mock_ping.return_value = False
        self.assertFalse(service.check_phone_presence())

    def test_check_phone_presence_empty_ips(self):
        service = PresenceService([])
        self.assertFalse(service.check_phone_presence())

    @patch('homeiot.clients.ping.is_any_phone_reachable')
    def test_is_present(self, mock_ping):
        service = PresenceService(['192.168.1.10'])

        # Motion detected overrides ping
        self.assertTrue(service.is_present(motion_detected=True))
        mock_ping.assert_not_called()

        # Motion not detected relies on ping
        mock_ping.return_value = True
        self.assertTrue(service.is_present(motion_detected=False))

        mock_ping.return_value = False
        self.assertFalse(service.is_present(motion_detected=False))


class TestHomeService(unittest.TestCase):
    '''HomeService のテスト'''

    def setUp(self):
        self.mock_config = MagicMock(spec=Config)
        self.mock_config.hue_on_scene_id = 'scene-123'
        self.mock_db = MagicMock()
        self.mock_db.get_roomy_lock.return_value = None
        self.mock_presence_service = MagicMock(spec=PresenceService)
        self.mock_hue_client = MagicMock()
        self.mock_ifttt_client = MagicMock()

        self.service = HomeService(
            config=self.mock_config,
            db_connector=self.mock_db,
            presence_service=self.mock_presence_service,
            hue_client=self.mock_hue_client,
            ifttt_client=self.mock_ifttt_client,
        )

    def test_is_lighting_time(self):
        # Default HUE_ON_BEGIN_HOUR = 17, HUE_ON_END_HOUR = 6
        dt_night = datetime(2026, 9, 20, 20, 0, 0)
        dt_midnight = datetime(2026, 9, 20, 2, 0, 0)
        dt_day = datetime(2026, 9, 20, 12, 0, 0)

        self.assertTrue(self.service.is_lighting_time(dt_night))
        self.assertTrue(self.service.is_lighting_time(dt_midnight))
        self.assertFalse(self.service.is_lighting_time(dt_day))

        # Test fallback to datetime.now()
        with patch('homeiot.services.home_service.datetime') as mock_dt:
            mock_dt.now.return_value = dt_night
            self.assertTrue(self.service.is_lighting_time())

    def test_is_lighting_time_non_overnight_range(self):
        with patch.object(constants, 'HUE_ON_BEGIN_HOUR', 8), patch.object(constants, 'HUE_ON_END_HOUR', 18):
            dt_morning = datetime(2026, 9, 20, 10, 0, 0)
            dt_night = datetime(2026, 9, 20, 20, 0, 0)
            self.assertTrue(self.service.is_lighting_time(dt_morning))
            self.assertFalse(self.service.is_lighting_time(dt_night))

    def test_is_roomy_sleeping_time(self):
        # Default ROOMY_SLEEP_START_HOUR = 22, ROOMY_SLEEP_END_HOUR = 6
        dt_night = datetime(2026, 9, 20, 23, 0, 0)
        dt_early = datetime(2026, 9, 20, 5, 0, 0)
        dt_noon = datetime(2026, 9, 20, 14, 0, 0)

        self.assertTrue(self.service.is_roomy_sleeping_time(dt_night))
        self.assertTrue(self.service.is_roomy_sleeping_time(dt_early))
        self.assertFalse(self.service.is_roomy_sleeping_time(dt_noon))

        # Test fallback to datetime.now()
        with patch('homeiot.services.home_service.datetime') as mock_dt:
            mock_dt.now.return_value = dt_night
            self.assertTrue(self.service.is_roomy_sleeping_time())

    def test_is_roomy_sleeping_time_non_overnight_range(self):
        with patch.object(constants, 'ROOMY_SLEEP_START_HOUR', 13), patch.object(
            constants, 'ROOMY_SLEEP_END_HOUR', 17
        ):
            dt_afternoon = datetime(2026, 9, 20, 15, 0, 0)
            dt_night = datetime(2026, 9, 20, 20, 0, 0)
            self.assertTrue(self.service.is_roomy_sleeping_time(dt_afternoon))
            self.assertFalse(self.service.is_roomy_sleeping_time(dt_night))

    def test_handle_presence_check_present_initial(self):
        self.mock_presence_service.is_present.return_value = True
        self.mock_db.get_last.side_effect = lambda key: None
        now = datetime(2026, 9, 20, 12, 0, 0)

        res = self.service.handle_presence_check(motion_detected=False, current_time=now)

        self.assertTrue(res)
        self.mock_db.set_last.assert_called_once_with(LastName.IN, now)
        self.mock_ifttt_client.dock_roomy.assert_not_called()
        self.mock_db.add_in_out_log.assert_not_called()

    def test_handle_presence_check_present_returning_from_out(self):
        self.mock_presence_service.is_present.return_value = True
        now = datetime(2026, 9, 20, 19, 0, 0)
        last_out = now - timedelta(minutes=10)

        def get_last_side_effect(name):
            if name == LastName.OUT:
                return last_out
            return None

        self.mock_db.get_last.side_effect = get_last_side_effect

        res = self.service.handle_presence_check(motion_detected=True, current_time=now)

        self.assertTrue(res)
        self.mock_db.set_last.assert_called_once_with(LastName.IN, now)
        self.mock_ifttt_client.dock_roomy.assert_called_once()
        self.mock_hue_client.activate_scene.assert_called_once_with(
            constants.HUE_ON_GROUP_ID, 'scene-123'
        )
        self.mock_ifttt_client.turn_on_ceiling_light.assert_called_once()
        self.mock_db.add_in_out_log.assert_called_once_with(InOutValue.IN, now)

    def test_handle_presence_check_present_returning_daytime_no_lighting(self):
        self.mock_presence_service.is_present.return_value = True
        now = datetime(2026, 9, 20, 12, 0, 0)
        last_out = now - timedelta(minutes=10)

        def get_last_side_effect(name):
            if name == LastName.OUT:
                return last_out
            return None

        self.mock_db.get_last.side_effect = get_last_side_effect

        res = self.service.handle_presence_check(motion_detected=False, current_time=now)

        self.assertTrue(res)
        self.mock_ifttt_client.dock_roomy.assert_called_once()
        self.mock_hue_client.activate_scene.assert_not_called()
        self.mock_ifttt_client.turn_on_ceiling_light.assert_not_called()
        self.mock_db.add_in_out_log.assert_called_once_with(InOutValue.IN, now)

    def test_handle_presence_check_present_returning_by_threshold(self):
        self.mock_presence_service.is_present.return_value = True
        now = datetime(2026, 9, 20, 12, 0, 0)
        last_in = now - timedelta(minutes=10)
        last_out = now - timedelta(seconds=constants.OUT_THRESHOLD_SECONDS + 1)

        def get_last_side_effect(name):
            if name == LastName.IN:
                return last_in
            if name == LastName.OUT:
                return last_out
            return None

        self.mock_db.get_last.side_effect = get_last_side_effect

        res = self.service.handle_presence_check(motion_detected=False, current_time=now)

        self.assertTrue(res)
        self.mock_ifttt_client.dock_roomy.assert_called_once()
        self.mock_db.add_in_out_log.assert_called_once_with(InOutValue.IN, now)

    def test_handle_presence_check_present_returning_without_hue_or_ifttt(self):
        service = HomeService(
            config=self.mock_config,
            db_connector=self.mock_db,
            presence_service=self.mock_presence_service,
            hue_client=None,
            ifttt_client=None,
        )
        self.mock_presence_service.is_present.return_value = True
        now = datetime(2026, 9, 20, 19, 0, 0)
        last_out = now - timedelta(minutes=10)

        def get_last_side_effect(name):
            if name == LastName.OUT:
                return last_out
            return None

        self.mock_db.get_last.side_effect = get_last_side_effect

        res = service.handle_presence_check(current_time=now)

        self.assertTrue(res)
        self.mock_db.add_in_out_log.assert_called_once_with(InOutValue.IN, now)

    def test_handle_presence_check_out_initial(self):
        self.mock_presence_service.is_present.return_value = False
        self.mock_db.get_last.return_value = None
        now = datetime(2026, 9, 20, 12, 0, 0)

        res = self.service.handle_presence_check(motion_detected=False, current_time=now)

        self.assertFalse(res)
        self.mock_db.set_last.assert_not_called()
        self.mock_db.add_in_out_log.assert_not_called()

    def test_handle_presence_check_out_thresholds(self):
        self.mock_presence_service.is_present.return_value = False
        now = datetime(2026, 9, 20, 14, 0, 0)
        last_in = now - timedelta(seconds=constants.HUE_THRESHOLD_SECONDS + 10)

        def get_last_side_effect(name):
            if name == LastName.IN:
                return last_in
            return None

        self.mock_db.get_last.side_effect = get_last_side_effect
        self.mock_hue_client.is_any_on.return_value = True
        self.mock_db.get_roomy_lock.return_value = None
        self.mock_ifttt_client.start_roomy.return_value = True

        res = self.service.handle_presence_check(motion_detected=False, current_time=now)

        self.assertFalse(res)
        self.mock_db.set_last.assert_any_call(LastName.OUT, now)
        self.mock_db.add_in_out_log.assert_called_once_with(InOutValue.OUT, now)

        # Light turning off
        self.mock_hue_client.turn_off_group.assert_called_once_with(constants.HUE_OFF_GROUP_ID)
        self.mock_ifttt_client.turn_off_ceiling_light.assert_called_once()
        self.mock_db.set_last.assert_any_call(LastName.HUE_OFF, now)

        # Roomy start
        self.mock_ifttt_client.start_roomy.assert_called_once()
        self.mock_db.set_last.assert_any_call(LastName.ROOMY, now)

    def test_handle_presence_check_out_already_recorded_out(self):
        self.mock_presence_service.is_present.return_value = False
        now = datetime(2026, 9, 20, 14, 0, 0)
        last_in = now - timedelta(seconds=constants.OUT_THRESHOLD_SECONDS + 10)
        last_out = now - timedelta(seconds=5)

        def get_last_side_effect(name):
            if name == LastName.IN:
                return last_in
            if name == LastName.OUT:
                return last_out
            return None

        self.mock_db.get_last.side_effect = get_last_side_effect

        self.service.handle_presence_check(motion_detected=False, current_time=now)

        # Since last_out > last_in, OUT log is not added again
        self.mock_db.add_in_out_log.assert_not_called()

    def test_check_and_turn_off_lights_hue_is_off(self):
        self.mock_presence_service.is_present.return_value = False
        now = datetime(2026, 9, 20, 14, 0, 0)
        last_in = now - timedelta(seconds=constants.HUE_THRESHOLD_SECONDS + 10)

        def get_last_side_effect(name):
            if name == LastName.IN:
                return last_in
            return None

        self.mock_db.get_last.side_effect = get_last_side_effect
        self.mock_hue_client.is_any_on.return_value = False

        self.service.handle_presence_check(motion_detected=False, current_time=now)

        self.mock_hue_client.turn_off_group.assert_not_called()
        self.mock_ifttt_client.turn_off_ceiling_light.assert_not_called()

    def test_check_and_turn_off_lights_no_clients(self):
        service = HomeService(
            config=self.mock_config,
            db_connector=self.mock_db,
            presence_service=self.mock_presence_service,
            hue_client=None,
            ifttt_client=None,
        )
        service._check_and_turn_off_lights(datetime.now())
        self.mock_db.set_last.assert_not_called()

    def test_check_and_start_roomy_skip_conditions(self):
        now = datetime(2026, 9, 20, 14, 0, 0)

        # 1. No IFTTT client
        service_no_ifttt = HomeService(
            config=self.mock_config,
            db_connector=self.mock_db,
            presence_service=self.mock_presence_service,
            ifttt_client=None,
        )
        service_no_ifttt._check_and_start_roomy(now)
        self.mock_db.set_last.assert_not_called()

        # 2. Night sleeping time
        night_time = datetime(2026, 9, 20, 23, 0, 0)
        self.service._check_and_start_roomy(night_time)
        self.mock_ifttt_client.start_roomy.assert_not_called()

        # 3. Locked by roomy_lock
        self.mock_db.get_roomy_lock.return_value = date(2026, 9, 20)
        self.service._check_and_start_roomy(now)
        self.mock_ifttt_client.start_roomy.assert_not_called()

        # 4. Already ran today
        self.mock_db.get_roomy_lock.return_value = None
        self.mock_db.get_last.return_value = datetime(2026, 9, 20, 10, 0, 0)
        self.service._check_and_start_roomy(now)
        self.mock_ifttt_client.start_roomy.assert_not_called()

    def test_handle_presence_check_default_current_time(self):
        self.mock_presence_service.is_present.return_value = True
        self.mock_db.get_last.return_value = None

        res = self.service.handle_presence_check()

        self.assertTrue(res)
        self.mock_db.set_last.assert_called_once()
