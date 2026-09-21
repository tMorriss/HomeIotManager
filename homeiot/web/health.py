'''HomeIotManager - ヘルスチェック ルーティングモジュール'''

from flask import Blueprint

health_bp = Blueprint('health', __name__)


@health_bp.route('/healthz', methods=['GET'])
def healthz():
    '''ヘルスチェックエンドポイント'''
    return '', 204
