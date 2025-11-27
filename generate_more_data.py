import psycopg2
from psycopg2.extras import execute_values
from app.core.config import settings
from datetime import datetime, timedelta
import random
import numpy as np

# Connect to database
conn = psycopg2.connect(
    host=settings.DB_HOST,
    port=settings.DB_PORT,
    dbname=settings.DB_NAME,
    user=settings.DB_USER,
    password=settings.DB_PASS
)
cur = conn.cursor()

# Clear existing data
cur.execute("DELETE FROM sensor_hourly")
conn.commit()

print("Generating 600+ hourly data points...")

# Generate data for the past 25 days (600 hours)
base_time = datetime(2025, 11, 2, 0, 0, 0)
records = []

for i in range(600):
    ts = base_time + timedelta(hours=i)
    
    # Realistic variations
    hour = ts.hour
    
    # Temperature: 22-28°C with daily cycle
    base_temp = 25 + 2 * np.sin((hour - 6) * np.pi / 12)
    temp = base_temp + random.uniform(-0.5, 0.5)
    
    # Humidity: 40-70% inverse to temperature
    humidity = 55 - (temp - 25) + random.uniform(-5, 5)
    
    # Wind speed: 0.5-3.5 m/s
    wind_speed = 1.5 + random.uniform(-0.5, 1.5)
    
    # PM2.5: 10-40 µg/m³
    pm25 = 20 + random.uniform(-8, 15)
    
    # CO2: 400-600 ppm
    co2 = 500 + random.uniform(-50, 50)
    
    # Energy: varies by hour (higher during day)
    energy_kwh = (5 if 6 <= hour <= 18 else 2) + random.uniform(-1, 2)
    
    # Cost: 1500 IDR per kWh
    cost_idr = energy_kwh * 1500
    
    # EUI: Energy Use Intensity (kWh/m²)
    eui_kwh_m2 = energy_kwh / 10  # assuming 10 m² area
    
    # PMV/PPD (comfort indices)
    pmv = (temp - 25) * 0.1 + random.uniform(-0.2, 0.2)
    if pmv < -3: pmv = -3
    if pmv > 3: pmv = 3
    ppd = 5 + abs(pmv) * 15
    
    pmv_label = "Dingin" if pmv < -0.5 else ("Hangat" if pmv > 0.5 else "Nyaman")
    
    dayofweek = ts.weekday()
    
    records.append((
        ts,
        round(temp, 2),
        round(humidity, 2),
        round(wind_speed, 2),
        round(pm25, 2),
        round(co2, 2),
        round(energy_kwh, 2),
        round(cost_idr, 2),
        round(eui_kwh_m2, 2),
        round(pmv, 2),
        round(ppd, 2),
        pmv_label,
        dayofweek,
        datetime.now()
    ))

# Insert data
insert_query = """
INSERT INTO sensor_hourly 
(ts, temp, humidity, wind_speed, pm25, co2, energy_kwh, cost_idr, eui_kwh_m2, pmv, ppd, pmv_label, dayofweek, created_at)
VALUES %s
"""

execute_values(cur, insert_query, records)
conn.commit()

# Verify
cur.execute("SELECT COUNT(*) FROM sensor_hourly")
count = cur.fetchone()[0]
cur.execute("SELECT ts, temp FROM sensor_hourly ORDER BY ts DESC LIMIT 1")
latest = cur.fetchone()

print(f"✓ Inserted {count} records")
print(f"✓ Latest: {latest[0]} - Temp: {latest[1]:.2f}°C")

cur.close()
conn.close()
