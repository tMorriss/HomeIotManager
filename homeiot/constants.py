'''HomeIotManager - 定数定義モジュール

システム内で使用される動作パラメータ・数値を一括管理します。
'''

from datetime import timedelta, timezone
from pathlib import Path

JAPAN_TIMEZONE = timezone(timedelta(hours=9))

PRESENCE_CHECK_INTERVAL_SECONDS = 10
PRESENCE_SENSOR_HEALTH_CHECK_INTERVAL_SECONDS = 600
OUT_THRESHOLD_SECONDS = 180
HUE_THRESHOLD_SECONDS = 600
LAST_IN_THRESHOLD_SECONDS = 180

HUE_ON_BEGIN_HOUR = 17
HUE_ON_END_HOUR = 6
ROOMY_SLEEP_START_HOUR = 22
ROOMY_SLEEP_END_HOUR = 6

HUE_CA_BUNDLE_PATH = str(Path(__file__).resolve().parents[1] / 'ca' / 'huebridge_cacert_bundle.pem')
HUE_API_TIMEOUT_SECONDS = 5.0

WEB_PORT = 8080
SWITCHBOT_API_BASE_URL = 'https://api.switch-bot.com'
SWITCHBOT_API_TIMEOUT_SECONDS = 5.0
