'''HomeIotManager - Web レスポンススキーマ モジュール'''

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    '''エラーレスポンス スキーマ'''
    message: str
