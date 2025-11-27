#!/usr/bin/env python3
"""Debug weekly forecast window calculation"""

from app.core.config import settings
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
import psycopg2

WIB = ZoneInfo('Asia/Jakarta')

# Connect to DB
conn = psycopg2.connect(
    host=settings.DB_HOST,
    port=settings.DB_PORT,
    dbname=settings.DB_NAME,
    user=settings.DB_USER,
    password=settings.DB_PASS
)
cur = conn.cursor()

# Check date range in database
cur.execute("SELECT MIN(ts), MAX(ts) FROM sensor_hourly")
min_ts, max_ts = cur.fetchone()
print(f"Database date range:")
print(f"  Min: {min_ts}")
print(f"  Max: {max_ts}")

# Check how many distinct DAYS exist
cur.execute("""
SELECT COUNT(DISTINCT DATE_TRUNC('day', ts AT TIME ZONE 'Asia/Jakarta')) as distinct_days
FROM sensor_hourly
""")
distinct_days = cur.fetchone()[0]
print(f"\nDistinct days in database: {distinct_days}")

# List all days
cur.execute("""
SELECT DISTINCT DATE_TRUNC('day', ts AT TIME ZONE 'Asia/Jakarta')::date as day
FROM sensor_hourly
ORDER BY day ASC
""")
days = cur.fetchall()
print(f"\nAll {len(days)} days available:")
for i, (day,) in enumerate(days[:5]):
    print(f"  {i+1}. {day}")
print(f"  ...")
for i, (day,) in enumerate(days[-3:], len(days)-2):
    print(f"  {i}. {day}")

# Now test the window calculation
ref_wib = datetime.now(tz=WIB)
print(f"\n{'='*70}")
print(f"Ref datetime (now): {ref_wib}")
print(f"{'='*70}")

# Current calculation
end = ref_wib.replace(hour=0, minute=0, second=0, microsecond=0)
start = end - timedelta(days=30)

print(f"\nFor days=30 (current code after my fix):")
print(f"  Start: {start}")
print(f"  End: {end}")

# Count data points in this window
start_utc = start.astimezone(ZoneInfo("UTC"))
end_utc = end.astimezone(ZoneInfo("UTC"))

cur.execute("""
SELECT COUNT(DISTINCT DATE_TRUNC('day', ts AT TIME ZONE 'Asia/Jakarta')::date) as days_in_range
FROM sensor_hourly
WHERE ts >= %s AND ts < %s
""", (start_utc, end_utc))
days_in_range = cur.fetchone()[0]
print(f"  Days matched in window: {days_in_range}")

# Try alternative: query from hari paling tua sampai hari sekarang
print(f"\n{'='*70}")
print("Alternative: Query ALL available data")
cur.execute("""
SELECT COUNT(DISTINCT DATE_TRUNC('day', ts AT TIME ZONE 'Asia/Jakarta')::date) as total_days
FROM sensor_hourly
""")
total_days = cur.fetchone()[0]
print(f"  Total distinct days available: {total_days}")

conn.close()
