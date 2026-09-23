'''HomeIotManager - FastAPI アプリケーションファクトリ モジュール

FastAPI アプリケーションの生成、環境設定、ルーターの登録を行います。
'''

import logging
from typing import Optional

from fastapi import FastAPI

from homeiot.clients.hue import HueClient
from homeiot.clients.ifttt import IftttClient
from homeiot.clients.switchbot import SwitchBotClient
from homeiot.config import Config
from homeiot.db.connector import DBConnector
from homeiot.services.home_service import HomeService
from homeiot.web.health import health_router
from homeiot.web.webhook import webhook_router

logger = logging.getLogger(__name__)


def create_app(
    config: Optional[Config] = None,
    db_connector: Optional[DBConnector] = None,
    switchbot_client: Optional[SwitchBotClient] = None,
    home_service: Optional[HomeService] = None,
) -> FastAPI:
    '''FastAPI アプリケーションインスタンスを生成・構築します。'''
    app = FastAPI(title='HomeIotManager')

    if config is None:
        config = Config()

    if db_connector is None:
        db_connector = DBConnector(config)

    if switchbot_client is None:
        switchbot_client = SwitchBotClient(config.switchbot_webhook_token)

    if home_service is None:
        hue_client = HueClient(config.hue_bridge_ip, config.hue_api_user)
        ifttt_client = IftttClient(config.ifttt_webhook_key)
        home_service = HomeService(
            config=config,
            db_connector=db_connector,
            hue_client=hue_client,
            ifttt_client=ifttt_client,
        )

    app.state.config_obj = config
    app.state.db_connector = db_connector
    app.state.switchbot_client = switchbot_client
    app.state.home_service = home_service

    app.include_router(health_router)
    app.include_router(webhook_router)

    return app
