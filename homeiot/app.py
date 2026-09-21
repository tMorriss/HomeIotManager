'''HomeIotManager - Flask アプリケーションファクトリ モジュール

Flask アプリケーションの生成、環境設定、Blueprint の登録を行います。
'''

import logging
from typing import Optional

from flask import Flask, jsonify

from homeiot.clients.hue import HueClient
from homeiot.clients.ifttt import IftttClient
from homeiot.clients.switchbot import SwitchBotClient
from homeiot.config import Config
from homeiot.db.connector import DBConnector
from homeiot.services.home_service import HomeService
from homeiot.web.webhook import webhook_bp

logger = logging.getLogger(__name__)


def create_app(
    config: Optional[Config] = None,
    db_connector: Optional[DBConnector] = None,
    switchbot_client: Optional[SwitchBotClient] = None,
    home_service: Optional[HomeService] = None,
) -> Flask:
    '''Flask アプリケーションインスタンスを生成・構築します。'''
    app = Flask(__name__)

    if config is None:
        config = Config()

    if db_connector is None:
        db_connector = DBConnector(config)

    if switchbot_client is None:
        switchbot_client = SwitchBotClient(config.switchbot_webhook_token)

    if home_service is None:
        hue_client = HueClient(config)
        ifttt_client = IftttClient(config)
        home_service = HomeService(
            config=config,
            db_connector=db_connector,
            hue_client=hue_client,
            ifttt_client=ifttt_client,
        )

    app.config['APP_CONFIG'] = config
    app.config['DB_CONNECTOR'] = db_connector
    app.config['SWITCHBOT_CLIENT'] = switchbot_client
    app.config['HOME_SERVICE'] = home_service

    app.register_blueprint(webhook_bp)

    @app.route('/healthz', methods=['GET'])
    def healthz():
        return jsonify({'status': 'ok'}), 200

    return app
