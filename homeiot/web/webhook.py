'''HomeIotManager - Webhook ルーティングモジュール

SwitchBot 人感センサー等からの Webhook イベントを受信・処理します。
'''

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response, status

logger = logging.getLogger(__name__)

webhook_router = APIRouter()


@webhook_router.post('/switchbot/all', status_code=status.HTTP_204_NO_CONTENT)
async def handle_switchbot_webhook(request: Request, token: Optional[str] = None):
    '''SwitchBot Webhook エンドポイント'''
    switchbot_client = request.app.state.switchbot_client
    home_service = request.app.state.home_service

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

    parsed = switchbot_client.parse_webhook_payload(payload)
    if not parsed.is_valid:
        logger.warning('Invalid SwitchBot webhook payload: %s', parsed.error)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid request',
        )

    if not parsed.is_motion_detected:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    try:
        # スマホPingで在宅を確認できる場合、人感センサーによる帰宅処理は不要。
        if not await home_service.is_present():
            await home_service.handle_presence_check(motion_detected=True)
    except Exception as exc:
        logger.error('Error occurred during presence check: %s', exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Internal Server Error',
        ) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
