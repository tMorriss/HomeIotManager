'''HomeIotManager - ヘルスチェック ルーティングモジュール'''

from fastapi import APIRouter, Response, status

health_router = APIRouter()


@health_router.get('/healthz', status_code=status.HTTP_204_NO_CONTENT)
def healthz():
    '''ヘルスチェックエンドポイント'''
    return Response(status_code=status.HTTP_204_NO_CONTENT)
