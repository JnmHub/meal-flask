# app/utils/tz.py
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

APP_TZ_NAME = os.getenv("APP_TZ", "Asia/Shanghai")
APP_TZ = ZoneInfo(APP_TZ_NAME)

def now_local():
    """上海时区的当前时间（aware datetime）"""
    return datetime.now(APP_TZ)

def to_local(dt: datetime | None) -> datetime | None:
    """把任意 datetime 转成上海时区（None 原样返回）"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # 你库里如果是 naive（无 tz），按 UTC 解释再转；否则直接转
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(APP_TZ)
