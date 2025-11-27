#!/usr/bin/env python3
"""
Simple test data generator untuk sensor_hourly table.
Jalankan sekali untuk populate test data.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import sys

sys.path.insert(0, '/Users/user/Documents/03 KERJA/PT Multimedia Solusi Prima/2025/NOVEMBER/BIMA')

from app.realtime.db import get_conn, init_table, insert_row
from app.realtime.generator import generate_hour

WIB = ZoneInfo("Asia/Jakarta")

def populate_test_data():
    """Generate 72 hours of test data (3 days)"""
    
    print("=" * 70)
    print("POPULATING TEST DATA")
    print("=" * 70)
    
    # Initialize table if not exists
    print("1. Initializing table...")
    try:
        init_table()
        print("   ✓ Table initialized")
    except Exception as e:
        print(f"   ✓ Table already exists (or init OK): {e}")
    
    # Generate 72 hours of data (3 days back from now)
    print("\n2. Generating test data (72 hours)...")
    now_wib = datetime.now(tz=WIB)
    start_time = now_wib - timedelta(hours=72)
    
    # Round to nearest hour
    start_time = start_time.replace(minute=0, second=0, microsecond=0)
    
    data_points = []
    current_time = start_time
    
    for i in range(72):
        try:
            row = generate_hour(current_time)
            data_points.append(row)
            current_time += timedelta(hours=1)
        except Exception as e:
            print(f"   ✗ Error generating hour {i}: {e}")
            return False
    
    print(f"   ✓ Generated {len(data_points)} hours of data")
    
    # Insert into database
    print("\n3. Inserting data into database...")
    inserted = 0
    skipped = 0
    
    for i, row in enumerate(data_points):
        try:
            insert_row(row)
            inserted += 1
            if (i + 1) % 12 == 0:
                print(f"   ✓ Inserted {i + 1}/{len(data_points)} rows")
        except Exception as e:
            if "UNIQUE violation" in str(e) or "CONFLICT" in str(e):
                skipped += 1
            else:
                print(f"   ✗ Error inserting row {i}: {e}")
    
    print(f"\n4. Result:")
    print(f"   ✓ Inserted: {inserted} rows")
    print(f"   → Skipped: {skipped} rows (already exist)")
    
    # Verify
    print("\n5. Verification...")
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM sensor_hourly")
            total = cur.fetchone()[0]
            print(f"   ✓ Total rows in sensor_hourly: {total}")
            
            if total >= 7:
                print(f"   ✓ Ready for forecast (minimum 7 datapoints needed)")
            else:
                print(f"   ⚠ Need more data ({total}/7 minimum)")
    except Exception as e:
        print(f"   ✗ Verification error: {e}")
        return False
    
    print("\n" + "=" * 70)
    print("✓ DATA POPULATION COMPLETE")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = populate_test_data()
    sys.exit(0 if success else 1)
