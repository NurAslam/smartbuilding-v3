#!/usr/bin/env python3
"""
Generate 30 additional days of data for weekly/monthly forecasts.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import sys

sys.path.insert(0, '/Users/user/Documents/03 KERJA/PT Multimedia Solusi Prima/2025/NOVEMBER/BIMA')

from app.realtime.db import get_conn, insert_row
from app.realtime.generator import generate_hour

WIB = ZoneInfo('Asia/Jakarta')

# Check current data
with get_conn() as conn, conn.cursor() as cur:
    cur.execute('SELECT COUNT(*) FROM sensor_hourly')
    current_count = cur.fetchone()[0]
    print(f'Current rows: {current_count}')
    
    # Get date range
    cur.execute('SELECT MIN(ts), MAX(ts) FROM sensor_hourly')
    min_ts, max_ts = cur.fetchone()
    print(f'Date range: {min_ts} to {max_ts}')

# Generate 30 days of data (before current data)
print(f'\nGenerating 30 days of additional data...')
now_wib = datetime.now(tz=WIB)
start_time = now_wib - timedelta(days=102)  # 102 days back (30 new + 72 existing)
start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)

inserted = 0
skipped = 0
for day in range(30):
    for hour in range(24):
        current_time = start_time + timedelta(days=day, hours=hour)
        try:
            row = generate_hour(current_time)
            insert_row(row)
            inserted += 1
        except Exception as e:
            if "UNIQUE" not in str(e) and "CONFLICT" not in str(e):
                print(f"Error on {current_time}: {e}")
            skipped += 1

print(f'Inserted: {inserted}')
print(f'Skipped/Duplicate: {skipped}')

# Check final count
with get_conn() as conn, conn.cursor() as cur:
    cur.execute('SELECT COUNT(*) FROM sensor_hourly')
    final_count = cur.fetchone()[0]
    print(f'Final rows: {final_count}')
    
    # Get new date range
    cur.execute('SELECT MIN(ts), MAX(ts) FROM sensor_hourly')
    min_ts, max_ts = cur.fetchone()
    print(f'New date range: {min_ts} to {max_ts}')
