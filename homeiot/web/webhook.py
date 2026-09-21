'''HomeIotManager - Webhook ルーティングモジュール

SwitchBot 人感センサー等からの Webhook イベントを受信・処理します。
'''

import logging

from flask import Blueprint, current_app, jsonify, request

logger = logging.getLogger(__name__)

webhook_bp = Blueprint('webhook', __name__)


@webhook_bp.route('/switchbot/all', methods=['POST'])
def handle_switchbot_webhook():
    '''SwitchBot Webhook エンドポイント'''
    token = request.args.get('token')

    if not current_app.switchbot_client.verify_token(token):
        logger.warning('Unauthorized SwitchBot webhook access attempt.')
        return jsonify({'message': 'Unauthorized'}), 401

    payload = request.get_json(silent=True) or {}
    parsed = current_app.switchbot_client.parse_webhook_payload(payload)
    is_motion_detected = parsed.get('is_motion_detected', False)

    current_app.home_service.handle_presence_check(motion_detected=is_motion_detected)

    return '', 204
