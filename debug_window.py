#!/usr/bin/env python3
"""Debug window calculations"""

from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
import psycopg2
from app.core.config import settings

WIB = ZoneInfo('Asia/Jakarta')
UTC = ZoneInfo('UTC')

ref_wib = datetime.now(tz=WIB)
print(f"Current time (WIB): {ref_wib}")
print()

# Simulate _calc_series_window("daily", 30, ref_wib)
def _calc_series_window_daily(size, ref_wib):
    end = ref_wib.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    start = end - timedelta(days=size)
    return start, end

start, end = _calc_series_window_daily(30, ref_wib)
print("_calc_series_window('daily', 30, ref_wib):")
print(f"  Start (WIB): {start}")
print(f"  End (WIB):   {end}")

start_utc = start.astimezone(UTC)
end_utc = end.astimezone(UTC)
print(f"  Start (UTC): {start_utc}")
print(f"  End (UTC):   {end_utc}")

# Check database
conn = psycopg2.connect(
    host=settings.DB_HOST,
    port=settings.DB_PORT,
    dbname=settings.DB_NAME,
    user=settings.DB_USER,
    password=settings.DB_PASS
)
cur = conn.cursor()

cur.execute("""
SELECT COUNT(DISTINCT DATE_TRUNC('day', ts AT TIME ZONE 'Asia/Jakarta')::date) as days_in_range
FROM sensor_hourly
WHERE ts >= %s AND ts < %s
""", (start_utc, end_utc))
days_in_range = cur.fetchone()[0]
print(f"  Days matched in DB: {days_in_range}")

# List which days are matched
cur.execute("""
SELECT DISTINCT DATE_TRUNC('day', ts AT TIME ZONE 'Asia/Jakarta')::date as day
FROM sensor_hourly
WHERE ts >= %s AND ts < %s
ORDER BY day ASC
""", (start_utc, end_utc))
days = [row[0] for row in cur.fetchall()]
print(f"  Days: {days[:3]} ... {days[-3:] if len(days) > 6 else days}")

print("\n" + "="*70)

# Simulate monthly
def _calc_series_window_monthly(size, ref_wib):
    end = ref_wib.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = (end.replace(day=28) + timedelta(days=4)).replace(day=1)
    start = end - timedelta(days=31 * size)
    return start, end

start, end = _calc_series_window_monthly(90, ref_wib)
print("_calc_series_window('monthly', 90, ref_wib):")
print(f"  Start (WIB): {start}")
print(f"  End (WIB):   {end}")

start_utc = start.astimezone(UTC)
end_utc = end.astimezone(UTC)
print(f"  Start (UTC): {start_utc}")
print(f"  End (UTC):   {end_utc}")

cur.execute("""
SELECT COUNT(DISTINCT DATE_TRUNC('day', ts AT TIME ZONE 'Asia/Jakarta')::date) as days_in_range
FROM sensor_hourly
WHERE ts >= %s AND ts < %s
""", (start_utc, end_utc))
days_in_range = cur.fetchone()[0]
print(f"  Days matched in DB: {days_in_range}")

conn.close()
