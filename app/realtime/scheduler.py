from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from zoneinfo import ZoneInfo
from app.core.config import settings
from .generator import generate_hour
from .db import insert_row

scheduler = BackgroundScheduler(timezone=settings.APP_TZ)
WIB = ZoneInfo(settings.APP_TZ)


@scheduler.scheduled_job("cron", minute=0)
def hourly_job():
    try:
        ts_now = datetime.now(tz=WIB)
        ts_hour = ts_now.replace(minute=0, second=0, microsecond=0)
        row = generate_hour(ts_hour)
        insert_row(row)
    except Exception as e:
        print("[scheduler] error:", e)
