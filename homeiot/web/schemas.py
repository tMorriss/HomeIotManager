'''HomeIotManager - Web レスポンススキーマ モジュール'''

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    '''エラーレスポンス スキーマ (RFC 9457 RFC Problem Details 準拠)'''
    title: str
