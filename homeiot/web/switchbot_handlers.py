'''HomeIotManager - SwitchBot Webhook デバイス別ハンドラー'''

import logging
from typing import Awaitable, Callable

from fastapi import Request

from homeiot.clients.switchbot import SwitchBotWebhookResult
from homeiot.db.connector import PresenceSensorValue

logger = logging.getLogger(__name__)


async def handle_presence_sensor(request: Request, event: SwitchBotWebhookResult) -> None:
    '''人感センサー Pro の状態を履歴テーブルに記録します。'''
    values = {
        'DETECTED': PresenceSensorValue.DETECTED,
        'NOT_DETECTED': PresenceSensorValue.NOT_DETECTED,
    }
    value = values.get(event.detection_state)
    if value is None:
        logger.warning('Ignoring unsupported Presence Sensor state: %s', event.detection_state)
        return

    await request.app.state.db_connector.add_presence_sensor_log(value, event.sample_time)


async def handle_legacy_presence(request: Request, event: SwitchBotWebhookResult) -> None:
    '''従来型人感センサーの検知を在宅判定へ渡します。'''
    if not event.is_motion_detected:
        return
    home_service = request.app.state.home_service
    if not await home_service.is_present():
        await home_service.handle_presence_check(motion_detected=True)


SwitchBotWebhookHandler = Callable[[Request, SwitchBotWebhookResult], Awaitable[None]]
DEVICE_HANDLERS: dict[str, SwitchBotWebhookHandler] = {
    'WoPresence': handle_legacy_presence,
    'Presence Sensor': handle_presence_sensor,
}


async def dispatch_switchbot_webhook(request: Request, event: SwitchBotWebhookResult) -> None:
    '''登録済みデバイスハンドラーへイベントを振り分けます。'''
    handler = DEVICE_HANDLERS.get(event.device_type)
    if handler is None:
        logger.info('Ignoring unsupported SwitchBot device type: %s', event.device_type)
        return
    await handler(request, event)
