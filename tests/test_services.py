'''HomeIotManager - サービス層単体テスト (非同期)'''

from datetime import date, datetime, timedelta

import pytest

from homeiot import constants
from homeiot.clients.hue import HueClient
from homeiot.clients.ifttt import IftttClient
from homeiot.config import Config
from homeiot.db.connector import InOutValue, LastName
from homeiot.services.home_service import HomeService


class TestHomeService:
    '''HomeService のテスト'''

    @pytest.fixture
    def home_service_setup(self, mocker):
        mock_config = mocker.MagicMock(spec=Config)
        mock_config.target_phone_ips = ['192.168.1.10']
        mock_config.hue_on_scene_id = 'scene-123'
        mock_db = mocker.MagicMock()
        mock_db.get_roomy_lock = mocker.AsyncMock(return_value=None)
        mock_db.get_last = mocker.AsyncMock(return_value=None)
        mock_db.set_last = mocker.AsyncMock()
        mock_db.add_in_out_log = mocker.AsyncMock()

        mock_hue_client = mocker.MagicMock(spec=HueClient)
        mock_hue_client.activate_scene = mocker.AsyncMock(return_value=True)
        mock_hue_client.turn_off_group = mocker.AsyncMock(return_value=True)
        mock_hue_client.is_any_on = mocker.AsyncMock(return_value=True)

        mock_ifttt_client = mocker.MagicMock(spec=IftttClient)
        mock_ifttt_client.dock_roomy = mocker.AsyncMock(return_value=True)
        mock_ifttt_client.start_roomy = mocker.AsyncMock(return_value=True)
        mock_ifttt_client.turn_on_ceiling_light = mocker.AsyncMock(return_value=True)
        mock_ifttt_client.turn_off_ceiling_light = mocker.AsyncMock(return_value=True)

        service = HomeService(
            config=mock_config,
            db_connector=mock_db,
            hue_client=mock_hue_client,
            ifttt_client=mock_ifttt_client,
        )
        return (
            service,
            mock_config,
            mock_db,
            mock_hue_client,
            mock_ifttt_client,
        )

    @pytest.mark.asyncio
    async def test_is_present(self, home_service_setup, mocker):
        service, _, _, _, _ = home_service_setup
        mock_ping = mocker.patch('homeiot.clients.ping.is_any_phone_reachable')
        mock_ping.return_value = True

        # Motion detected overrides ping
        assert await service.is_present(motion_detected=True) is True
        mock_ping.assert_not_called()

        # Motion not detected relies on ping
        assert await service.is_present(motion_detected=False) is True
        mock_ping.assert_called_once_with(['192.168.1.10'])

        mock_ping.reset_mock()
        mock_ping.return_value = False
        assert await service.is_present(motion_detected=False) is False

    @pytest.mark.asyncio
    async def test_is_present_no_ips(self, home_service_setup):
        service, mock_config, _, _, _ = home_service_setup
        mock_config.target_phone_ips = []
        assert await service.is_present(motion_detected=False) is False

    def test_is_lighting_time(self, home_service_setup, mocker):
        service, _, _, _, _ = home_service_setup
        # Default HUE_ON_BEGIN_HOUR = 17, HUE_ON_END_HOUR = 6
        dt_night = datetime(2026, 9, 20, 20, 0, 0)
        dt_midnight = datetime(2026, 9, 20, 2, 0, 0)
        dt_day = datetime(2026, 9, 20, 12, 0, 0)

        assert service.is_lighting_time(dt_night) is True
        assert service.is_lighting_time(dt_midnight) is True
        assert service.is_lighting_time(dt_day) is False

        # Test fallback to datetime.now()
        mock_dt = mocker.patch('homeiot.services.home_service.datetime')
        mock_dt.now.return_value = dt_night
        assert service.is_lighting_time() is True

    def test_is_lighting_time_non_overnight_range(self, home_service_setup, monkeypatch):
        service, _, _, _, _ = home_service_setup
        monkeypatch.setattr(constants, 'HUE_ON_BEGIN_HOUR', 8)
        monkeypatch.setattr(constants, 'HUE_ON_END_HOUR', 18)
        dt_morning = datetime(2026, 9, 20, 10, 0, 0)
        dt_night = datetime(2026, 9, 20, 20, 0, 0)
        assert service.is_lighting_time(dt_morning) is True
        assert service.is_lighting_time(dt_night) is False

    def test_is_roomy_sleeping_time(self, home_service_setup, mocker):
        service, _, _, _, _ = home_service_setup
        # Default ROOMY_SLEEP_START_HOUR = 22, ROOMY_SLEEP_END_HOUR = 6
        dt_night = datetime(2026, 9, 20, 23, 0, 0)
        dt_early = datetime(2026, 9, 20, 5, 0, 0)
        dt_noon = datetime(2026, 9, 20, 14, 0, 0)

        assert service.is_roomy_sleeping_time(dt_night) is True
        assert service.is_roomy_sleeping_time(dt_early) is True
        assert service.is_roomy_sleeping_time(dt_noon) is False

        # Test fallback to datetime.now()
        mock_dt = mocker.patch('homeiot.services.home_service.datetime')
        mock_dt.now.return_value = dt_night
        assert service.is_roomy_sleeping_time() is True

    def test_is_roomy_sleeping_time_non_overnight_range(self, home_service_setup, monkeypatch):
        service, _, _, _, _ = home_service_setup
        monkeypatch.setattr(constants, 'ROOMY_SLEEP_START_HOUR', 13)
        monkeypatch.setattr(constants, 'ROOMY_SLEEP_END_HOUR', 17)
        dt_afternoon = datetime(2026, 9, 20, 15, 0, 0)
        dt_night = datetime(2026, 9, 20, 20, 0, 0)
        assert service.is_roomy_sleeping_time(dt_afternoon) is True
        assert service.is_roomy_sleeping_time(dt_night) is False

    @pytest.mark.asyncio
    async def test_handle_presence_check_present_initial(self, home_service_setup, mocker):
        service, _, mock_db, _, mock_ifttt_client = home_service_setup
        mocker.patch.object(HomeService, 'is_present', return_value=True)
        mock_db.get_last.side_effect = lambda key: None
        now = datetime(2026, 9, 20, 12, 0, 0)

        res = await service.handle_presence_check(motion_detected=False, current_time=now)

        assert res is True
        mock_db.set_last.assert_called_once_with(LastName.IN, now)
        mock_ifttt_client.dock_roomy.assert_not_called()
        mock_db.add_in_out_log.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_presence_check_present_returning_from_out(self, home_service_setup, mocker):
        service, _, mock_db, mock_hue_client, mock_ifttt_client = home_service_setup
        mocker.patch.object(HomeService, 'is_present', return_value=True)
        now = datetime(2026, 9, 20, 19, 0, 0)
        last_out = now - timedelta(minutes=10)

        async def get_last_side_effect(name):
            if name == LastName.OUT:
                return last_out
            return None

        mock_db.get_last.side_effect = get_last_side_effect

        res = await service.handle_presence_check(motion_detected=True, current_time=now)

        assert res is True
        mock_db.set_last.assert_called_once_with(LastName.IN, now)
        mock_ifttt_client.dock_roomy.assert_called_once()
        mock_hue_client.activate_scene.assert_called_once_with(
            constants.HUE_ON_GROUP_ID, 'scene-123'
        )
        mock_ifttt_client.turn_on_ceiling_light.assert_called_once()
        mock_db.add_in_out_log.assert_called_once_with(InOutValue.IN, now)

    @pytest.mark.asyncio
    async def test_handle_presence_check_present_returning_daytime_no_lighting(self, home_service_setup, mocker):
        service, _, mock_db, mock_hue_client, mock_ifttt_client = home_service_setup
        mocker.patch.object(HomeService, 'is_present', return_value=True)
        now = datetime(2026, 9, 20, 12, 0, 0)
        last_out = now - timedelta(minutes=10)

        async def get_last_side_effect(name):
            if name == LastName.OUT:
                return last_out
            return None

        mock_db.get_last.side_effect = get_last_side_effect

        res = await service.handle_presence_check(motion_detected=False, current_time=now)

        assert res is True
        mock_ifttt_client.dock_roomy.assert_called_once()
        mock_hue_client.activate_scene.assert_not_called()
        mock_ifttt_client.turn_on_ceiling_light.assert_not_called()
        mock_db.add_in_out_log.assert_called_once_with(InOutValue.IN, now)

    @pytest.mark.asyncio
    async def test_handle_presence_check_present_returning_by_threshold(self, home_service_setup, mocker):
        service, _, mock_db, _, mock_ifttt_client = home_service_setup
        mocker.patch.object(HomeService, 'is_present', return_value=True)
        now = datetime(2026, 9, 20, 12, 0, 0)
        last_in = now - timedelta(minutes=10)
        last_out = now - timedelta(seconds=constants.OUT_THRESHOLD_SECONDS + 1)

        async def get_last_side_effect(name):
            if name == LastName.IN:
                return last_in
            if name == LastName.OUT:
                return last_out
            return None

        mock_db.get_last.side_effect = get_last_side_effect

        res = await service.handle_presence_check(motion_detected=False, current_time=now)

        assert res is True
        mock_ifttt_client.dock_roomy.assert_called_once()
        mock_db.add_in_out_log.assert_called_once_with(InOutValue.IN, now)

    @pytest.mark.asyncio
    async def test_handle_presence_check_out_initial(self, home_service_setup, mocker):
        service, _, mock_db, _, _ = home_service_setup
        mocker.patch.object(HomeService, 'is_present', return_value=False)
        mock_db.get_last.return_value = None
        now = datetime(2026, 9, 20, 12, 0, 0)

        res = await service.handle_presence_check(motion_detected=False, current_time=now)

        assert res is False
        mock_db.set_last.assert_not_called()
        mock_db.add_in_out_log.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_presence_check_out_thresholds(self, home_service_setup, mocker):
        service, _, mock_db, mock_hue_client, mock_ifttt_client = home_service_setup
        mocker.patch.object(HomeService, 'is_present', return_value=False)
        now = datetime(2026, 9, 20, 14, 0, 0)
        last_in = now - timedelta(seconds=constants.HUE_THRESHOLD_SECONDS + 10)

        async def get_last_side_effect(name):
            if name == LastName.IN:
                return last_in
            return None

        mock_db.get_last.side_effect = get_last_side_effect
        mock_hue_client.is_any_on.return_value = True
        mock_db.get_roomy_lock.return_value = None
        mock_ifttt_client.start_roomy.return_value = True

        res = await service.handle_presence_check(motion_detected=False, current_time=now)

        assert res is False
        mock_db.set_last.assert_any_call(LastName.OUT, now)
        mock_db.add_in_out_log.assert_called_once_with(InOutValue.OUT, now)

        # Light turning off
        mock_hue_client.turn_off_group.assert_called_once_with(constants.HUE_OFF_GROUP_ID)
        mock_ifttt_client.turn_off_ceiling_light.assert_called_once()

        # Roomy start
        mock_ifttt_client.start_roomy.assert_called_once()
        mock_db.set_last.assert_any_call(LastName.ROOMY, now)

    @pytest.mark.asyncio
    async def test_handle_presence_check_out_already_recorded_out(self, home_service_setup, mocker):
        service, _, mock_db, _, _ = home_service_setup
        mocker.patch.object(HomeService, 'is_present', return_value=False)
        now = datetime(2026, 9, 20, 14, 0, 0)
        last_in = now - timedelta(seconds=constants.OUT_THRESHOLD_SECONDS + 10)
        last_out = now - timedelta(seconds=5)

        async def get_last_side_effect(name):
            if name == LastName.IN:
                return last_in
            if name == LastName.OUT:
                return last_out
            return None

        mock_db.get_last.side_effect = get_last_side_effect

        await service.handle_presence_check(motion_detected=False, current_time=now)

        # Since last_out > last_in, OUT log is not added again
        mock_db.add_in_out_log.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_and_turn_off_lights_hue_is_off(self, home_service_setup, mocker):
        service, _, mock_db, mock_hue_client, mock_ifttt_client = home_service_setup
        mocker.patch.object(HomeService, 'is_present', return_value=False)
        now = datetime(2026, 9, 20, 14, 0, 0)
        last_in = now - timedelta(seconds=constants.HUE_THRESHOLD_SECONDS + 10)

        async def get_last_side_effect(name):
            if name == LastName.IN:
                return last_in
            return None

        mock_db.get_last.side_effect = get_last_side_effect
        mock_hue_client.is_any_on.return_value = False

        await service.handle_presence_check(motion_detected=False, current_time=now)

        mock_hue_client.turn_off_group.assert_not_called()
        mock_ifttt_client.turn_off_ceiling_light.assert_not_called()
        mock_db.set_last.assert_any_call(LastName.HUE_OFF, now)

    @pytest.mark.asyncio
    async def test_check_and_turn_off_lights_already_off_for_this_outing(self, home_service_setup, mocker):
        service, _, mock_db, mock_hue_client, mock_ifttt_client = home_service_setup
        mocker.patch.object(HomeService, 'is_present', return_value=False)
        now = datetime(2026, 9, 20, 14, 0, 0)
        last_in = now - timedelta(seconds=constants.HUE_THRESHOLD_SECONDS + 10)
        last_hue_off = now - timedelta(seconds=100)

        async def get_last_side_effect(name):
            if name == LastName.IN:
                return last_in
            if name == LastName.HUE_OFF:
                return last_hue_off
            return None

        mock_db.get_last.side_effect = get_last_side_effect

        await service.handle_presence_check(motion_detected=False, current_time=now)

        mock_hue_client.turn_off_group.assert_not_called()
        mock_ifttt_client.turn_off_ceiling_light.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_and_start_roomy_skip_conditions(self, home_service_setup):
        service, _, mock_db, _, mock_ifttt_client = home_service_setup
        now = datetime(2026, 9, 20, 14, 0, 0)
        last_in = now - timedelta(minutes=30)

        # 1. Night sleeping time
        night_time = datetime(2026, 9, 20, 23, 0, 0)
        await service._check_and_start_roomy(last_in, night_time)
        mock_ifttt_client.start_roomy.assert_not_called()

        # 2. Locked by roomy_lock
        mock_db.get_roomy_lock.return_value = date(2026, 9, 20)
        await service._check_and_start_roomy(last_in, now)
        mock_ifttt_client.start_roomy.assert_not_called()

        # 3. Already ran after last_in
        mock_db.get_roomy_lock.return_value = None
        mock_db.get_last.return_value = last_in + timedelta(minutes=5)
        await service._check_and_start_roomy(last_in, now)
        mock_ifttt_client.start_roomy.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_presence_check_default_current_time(self, home_service_setup, mocker):
        service, _, mock_db, _, _ = home_service_setup
        mocker.patch.object(HomeService, 'is_present', return_value=True)
        mock_db.get_last.return_value = None

        res = await service.handle_presence_check()

        assert res is True
        mock_db.set_last.assert_called_once()
