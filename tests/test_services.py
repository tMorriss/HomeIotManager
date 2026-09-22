'''HomeIotManager - サービス層単体テスト (非同期)'''

import unittest
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from homeiot import constants
from homeiot.clients.hue import HueClient
from homeiot.clients.ifttt import IftttClient
from homeiot.config import Config
from homeiot.db.connector import InOutValue, LastName
from homeiot.services.home_service import HomeService


class TestHomeService(unittest.IsolatedAsyncioTestCase):
    '''HomeService のテスト'''

    async def asyncSetUp(self):
        self.mock_config = MagicMock(spec=Config)
        self.mock_config.target_phone_ips = ['192.168.1.10']
        self.mock_config.hue_on_scene_id = 'scene-123'
        self.mock_db = MagicMock()
        self.mock_db.get_roomy_lock = AsyncMock(return_value=None)
        self.mock_db.get_last = AsyncMock(return_value=None)
        self.mock_db.set_last = AsyncMock()
        self.mock_db.add_in_out_log = AsyncMock()

        self.mock_hue_client = MagicMock(spec=HueClient)
        self.mock_hue_client.activate_scene = AsyncMock(return_value=True)
        self.mock_hue_client.turn_off_group = AsyncMock(return_value=True)
        self.mock_hue_client.is_any_on = AsyncMock(return_value=True)

        self.mock_ifttt_client = MagicMock(spec=IftttClient)
        self.mock_ifttt_client.dock_roomy = AsyncMock(return_value=True)
        self.mock_ifttt_client.start_roomy = AsyncMock(return_value=True)
        self.mock_ifttt_client.turn_on_ceiling_light = AsyncMock(return_value=True)
        self.mock_ifttt_client.turn_off_ceiling_light = AsyncMock(return_value=True)

        self.service = HomeService(
            config=self.mock_config,
            db_connector=self.mock_db,
            hue_client=self.mock_hue_client,
            ifttt_client=self.mock_ifttt_client,
        )

    @patch('homeiot.clients.ping.is_any_phone_reachable')
    async def test_is_present(self, mock_ping):
        mock_ping.return_value = True

        # Motion detected overrides ping
        self.assertTrue(await self.service.is_present(motion_detected=True))
        mock_ping.assert_not_called()

        # Motion not detected relies on ping
        self.assertTrue(await self.service.is_present(motion_detected=False))
        mock_ping.assert_called_once_with(['192.168.1.10'])

        mock_ping.reset_mock()
        mock_ping.return_value = False
        self.assertFalse(await self.service.is_present(motion_detected=False))

    async def test_is_present_no_ips(self):
        self.mock_config.target_phone_ips = []
        self.assertFalse(await self.service.is_present(motion_detected=False))

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

    @patch('homeiot.services.home_service.HomeService.is_present')
    async def test_handle_presence_check_present_initial(self, mock_is_present):
        mock_is_present.return_value = True
        self.mock_db.get_last.side_effect = lambda key: None
        now = datetime(2026, 9, 20, 12, 0, 0)

        res = await self.service.handle_presence_check(motion_detected=False, current_time=now)

        self.assertTrue(res)
        self.mock_db.set_last.assert_called_once_with(LastName.IN, now)
        self.mock_ifttt_client.dock_roomy.assert_not_called()
        self.mock_db.add_in_out_log.assert_not_called()

    @patch('homeiot.services.home_service.HomeService.is_present')
    async def test_handle_presence_check_present_returning_from_out(self, mock_is_present):
        mock_is_present.return_value = True
        now = datetime(2026, 9, 20, 19, 0, 0)
        last_out = now - timedelta(minutes=10)

        async def get_last_side_effect(name):
            if name == LastName.OUT:
                return last_out
            return None

        self.mock_db.get_last.side_effect = get_last_side_effect

        res = await self.service.handle_presence_check(motion_detected=True, current_time=now)

        self.assertTrue(res)
        self.mock_db.set_last.assert_called_once_with(LastName.IN, now)
        self.mock_ifttt_client.dock_roomy.assert_called_once()
        self.mock_hue_client.activate_scene.assert_called_once_with(
            constants.HUE_ON_GROUP_ID, 'scene-123'
        )
        self.mock_ifttt_client.turn_on_ceiling_light.assert_called_once()
        self.mock_db.add_in_out_log.assert_called_once_with(InOutValue.IN, now)

    @patch('homeiot.services.home_service.HomeService.is_present')
    async def test_handle_presence_check_present_returning_daytime_no_lighting(self, mock_is_present):
        mock_is_present.return_value = True
        now = datetime(2026, 9, 20, 12, 0, 0)
        last_out = now - timedelta(minutes=10)

        async def get_last_side_effect(name):
            if name == LastName.OUT:
                return last_out
            return None

        self.mock_db.get_last.side_effect = get_last_side_effect

        res = await self.service.handle_presence_check(motion_detected=False, current_time=now)

        self.assertTrue(res)
        self.mock_ifttt_client.dock_roomy.assert_called_once()
        self.mock_hue_client.activate_scene.assert_not_called()
        self.mock_ifttt_client.turn_on_ceiling_light.assert_not_called()
        self.mock_db.add_in_out_log.assert_called_once_with(InOutValue.IN, now)

    @patch('homeiot.services.home_service.HomeService.is_present')
    async def test_handle_presence_check_present_returning_by_threshold(self, mock_is_present):
        mock_is_present.return_value = True
        now = datetime(2026, 9, 20, 12, 0, 0)
        last_in = now - timedelta(minutes=10)
        last_out = now - timedelta(seconds=constants.OUT_THRESHOLD_SECONDS + 1)

        async def get_last_side_effect(name):
            if name == LastName.IN:
                return last_in
            if name == LastName.OUT:
                return last_out
            return None

        self.mock_db.get_last.side_effect = get_last_side_effect

        res = await self.service.handle_presence_check(motion_detected=False, current_time=now)

        self.assertTrue(res)
        self.mock_ifttt_client.dock_roomy.assert_called_once()
        self.mock_db.add_in_out_log.assert_called_once_with(InOutValue.IN, now)

    @patch('homeiot.services.home_service.HomeService.is_present')
    async def test_handle_presence_check_out_initial(self, mock_is_present):
        mock_is_present.return_value = False
        self.mock_db.get_last.return_value = None
        now = datetime(2026, 9, 20, 12, 0, 0)

        res = await self.service.handle_presence_check(motion_detected=False, current_time=now)

        self.assertFalse(res)
        self.mock_db.set_last.assert_not_called()
        self.mock_db.add_in_out_log.assert_not_called()

    @patch('homeiot.services.home_service.HomeService.is_present')
    async def test_handle_presence_check_out_thresholds(self, mock_is_present):
        mock_is_present.return_value = False
        now = datetime(2026, 9, 20, 14, 0, 0)
        last_in = now - timedelta(seconds=constants.HUE_THRESHOLD_SECONDS + 10)

        async def get_last_side_effect(name):
            if name == LastName.IN:
                return last_in
            return None

        self.mock_db.get_last.side_effect = get_last_side_effect
        self.mock_hue_client.is_any_on.return_value = True
        self.mock_db.get_roomy_lock.return_value = None
        self.mock_ifttt_client.start_roomy.return_value = True

        res = await self.service.handle_presence_check(motion_detected=False, current_time=now)

        self.assertFalse(res)
        self.mock_db.set_last.assert_any_call(LastName.OUT, now)
        self.mock_db.add_in_out_log.assert_called_once_with(InOutValue.OUT, now)

        # Light turning off
        self.mock_hue_client.turn_off_group.assert_called_once_with(constants.HUE_OFF_GROUP_ID)
        self.mock_ifttt_client.turn_off_ceiling_light.assert_called_once()

        # Roomy start
        self.mock_ifttt_client.start_roomy.assert_called_once()
        self.mock_db.set_last.assert_any_call(LastName.ROOMY, now)

    @patch('homeiot.services.home_service.HomeService.is_present')
    async def test_handle_presence_check_out_already_recorded_out(self, mock_is_present):
        mock_is_present.return_value = False
        now = datetime(2026, 9, 20, 14, 0, 0)
        last_in = now - timedelta(seconds=constants.OUT_THRESHOLD_SECONDS + 10)
        last_out = now - timedelta(seconds=5)

        async def get_last_side_effect(name):
            if name == LastName.IN:
                return last_in
            if name == LastName.OUT:
                return last_out
            return None

        self.mock_db.get_last.side_effect = get_last_side_effect

        await self.service.handle_presence_check(motion_detected=False, current_time=now)

        # Since last_out > last_in, OUT log is not added again
        self.mock_db.add_in_out_log.assert_not_called()

    @patch('homeiot.services.home_service.HomeService.is_present')
    async def test_check_and_turn_off_lights_hue_is_off(self, mock_is_present):
        mock_is_present.return_value = False
        now = datetime(2026, 9, 20, 14, 0, 0)
        last_in = now - timedelta(seconds=constants.HUE_THRESHOLD_SECONDS + 10)

        async def get_last_side_effect(name):
            if name == LastName.IN:
                return last_in
            return None

        self.mock_db.get_last.side_effect = get_last_side_effect
        self.mock_hue_client.is_any_on.return_value = False

        await self.service.handle_presence_check(motion_detected=False, current_time=now)

        self.mock_hue_client.turn_off_group.assert_not_called()
        self.mock_ifttt_client.turn_off_ceiling_light.assert_not_called()
        self.mock_db.set_last.assert_any_call(LastName.HUE_OFF, now)

    @patch('homeiot.services.home_service.HomeService.is_present')
    async def test_check_and_turn_off_lights_already_off_for_this_outing(self, mock_is_present):
        mock_is_present.return_value = False
        now = datetime(2026, 9, 20, 14, 0, 0)
        last_in = now - timedelta(seconds=constants.HUE_THRESHOLD_SECONDS + 10)
        last_hue_off = now - timedelta(seconds=100)

        async def get_last_side_effect(name):
            if name == LastName.IN:
                return last_in
            if name == LastName.HUE_OFF:
                return last_hue_off
            return None

        self.mock_db.get_last.side_effect = get_last_side_effect

        await self.service.handle_presence_check(motion_detected=False, current_time=now)

        self.mock_hue_client.turn_off_group.assert_not_called()
        self.mock_ifttt_client.turn_off_ceiling_light.assert_not_called()

    async def test_check_and_start_roomy_skip_conditions(self):
        now = datetime(2026, 9, 20, 14, 0, 0)
        last_in = now - timedelta(minutes=30)

        # 1. Night sleeping time
        night_time = datetime(2026, 9, 20, 23, 0, 0)
        await self.service._check_and_start_roomy(last_in, night_time)
        self.mock_ifttt_client.start_roomy.assert_not_called()

        # 2. Locked by roomy_lock
        self.mock_db.get_roomy_lock.return_value = date(2026, 9, 20)
        await self.service._check_and_start_roomy(last_in, now)
        self.mock_ifttt_client.start_roomy.assert_not_called()

        # 3. Already ran after last_in
        self.mock_db.get_roomy_lock.return_value = None
        self.mock_db.get_last.return_value = last_in + timedelta(minutes=5)
        await self.service._check_and_start_roomy(last_in, now)
        self.mock_ifttt_client.start_roomy.assert_not_called()

    @patch('homeiot.services.home_service.HomeService.is_present')
    async def test_handle_presence_check_default_current_time(self, mock_is_present):
        mock_is_present.return_value = True
        self.mock_db.get_last.return_value = None

        res = await self.service.handle_presence_check()

        self.assertTrue(res)
        self.mock_db.set_last.assert_called_once()


if __name__ == '__main__':
    unittest.main()
