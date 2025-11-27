#!/usr/bin/env python3
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
import psycopg2
from app.core.config import settings

WIB = ZoneInfo('Asia/Jakarta')
UTC = ZoneInfo('UTC')

ref_wib = datetime.now(tz=WIB)
print(f"Ref: {ref_wib}\n")

# Test window
end = ref_wib.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=2)
start = end - timedelta(days=30)

print(f"Window WIB: {start} to {end}")
start_utc = start.astimezone(UTC)
end_utc = end.astimezone(UTC)
print(f"Window UTC: {start_utc} to {end_utc}\n")

# Query
conn = psycopg2.connect(
    host=settings.DB_HOST, port=settings.DB_PORT, dbname=settings.DB_NAME, 
    user=settings.DB_USER, password=settings.DB_PASS
)
cur = conn.cursor()

cur.execute("""
SELECT DISTINCT DATE_TRUNC('day', ts AT TIME ZONE 'Asia/Jakarta')::date as day
FROM sensor_hourly
WHERE ts >= %s AND ts < %s
ORDER BY day ASC
""", (start_utc, end_utc))

days = [row[0] for row in cur.fetchall()]
print(f"Days matched: {len(days)}")
if days:
    print(f"First: {days[0]}, Last: {days[-1]}")
    
# Try without +2
print("\n" + "="*60)
end2 = ref_wib.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
start2 = end2 - timedelta(days=30)
print(f"WITHOUT +2:")
print(f"Window WIB: {start2} to {end2}")
start_utc2 = start2.astimezone(UTC)
end_utc2 = end2.astimezone(UTC)
print(f"Window UTC: {start_utc2} to {end_utc2}\n")

cur.execute("""
SELECT COUNT(DISTINCT DATE_TRUNC('day', ts AT TIME ZONE 'Asia/Jakarta')::date) as cnt
FROM sensor_hourly
WHERE ts >= %s AND ts < %s
""", (start_utc2, end_utc2))
cnt = cur.fetchone()[0]
print(f"Days matched: {cnt}")

conn.close()
