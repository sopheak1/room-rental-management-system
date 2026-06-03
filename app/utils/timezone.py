from datetime import datetime, date
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Asia/Phnom_Penh')  # UTC+7

def now():
    """Current datetime in UTC+7."""
    return datetime.now(TZ)

def today():
    """Current date in UTC+7."""
    return datetime.now(TZ).date()
