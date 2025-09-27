from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from zoneinfo import ZoneInfo
import logging

from app.core.config import settings
from .generator import generate_hour
from .db import insert_row

# gunakan AsyncIOScheduler agar satu event loop dengan FastAPI
scheduler = AsyncIOScheduler(timezone=settings.APP_TZ)
WIB = ZoneInfo(settings.APP_TZ)

def hourly_job():

    try:
        ts_now = datetime.now(tz=WIB)
        ts_hour = ts_now.replace(minute=0, second=0, microsecond=0)
        row = generate_hour(ts_hour)
        insert_row(row)
    except Exception:
        logging.exception("[scheduler] error saat hourly_job")

def setup_scheduler():
    trigger = CronTrigger(minute=0, second=0, timezone=settings.APP_TZ)
    # replace_existing=True agar tidak dobel ketika auto-reload / restart
    scheduler.add_job(
        hourly_job,
        trigger=trigger,
        id="hourly_gen",
        replace_existing=True,
        misfire_grace_time=600,  # toleransi 10 menit jika sempat sleep
    )
