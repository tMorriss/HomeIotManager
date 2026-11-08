'''HomeIotManager - Webhook ルーティングモジュール

SwitchBot 人感センサー等からの Webhook イベントを受信・処理します。
'''

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response, status

from homeiot.clients.switchbot import SwitchBotWebhookError
from homeiot.web.switchbot_handlers import dispatch_switchbot_webhook

logger = logging.getLogger(__name__)

webhook_router = APIRouter()


@webhook_router.post('/switchbot/all', status_code=status.HTTP_204_NO_CONTENT)
async def handle_switchbot_webhook(request: Request, token: Optional[str] = None):
    '''SwitchBot Webhook エンドポイント'''
    switchbot_client = request.app.state.switchbot_client
    if not switchbot_client.verify_token(token):
        logger.warning('Unauthorized SwitchBot webhook access attempt.')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Unauthorized',
        )

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    logger.info('SwitchBot webhook request body: %s', json.dumps(payload, ensure_ascii=False))

    try:
        parsed = switchbot_client.parse_webhook_payload(payload)
    except SwitchBotWebhookError as exc:
        logger.warning('Invalid SwitchBot webhook payload: %s', exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid request',
        ) from exc

    try:
        await dispatch_switchbot_webhook(request, parsed)
    except Exception as exc:
        logger.error('Error occurred during SwitchBot webhook handling: %s', exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Internal Server Error',
        ) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
