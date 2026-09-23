'''HomeIotManager - Webhook ルーティングモジュール

SwitchBot 人感センサー等からの Webhook イベントを受信・処理します。
'''

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response, status

from homeiot.web.schemas import ErrorResponse

logger = logging.getLogger(__name__)

webhook_router = APIRouter()


@webhook_router.post(
    '/switchbot/all',
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {'model': ErrorResponse, 'description': 'Unauthorized'},
        500: {'model': ErrorResponse, 'description': 'Internal Server Error'},
    },
)
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

    parsed = switchbot_client.parse_webhook_payload(payload)
    is_motion_detected = parsed.get('is_motion_detected', False)

    await home_service.handle_presence_check(motion_detected=is_motion_detected)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
