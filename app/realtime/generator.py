import math
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import numpy as np
from app.core.config import settings

WIB = ZoneInfo(settings.APP_TZ)
np.random.seed(123)

TEMP_BANDS = [18, 20, 23, 27, 29, 32]
PMV_LABELS = {
    -3: "sangat dingin", -2: "dingin", -1: "agak dingin",
     0: "netral (nyaman)", +1: "agak panas", +2: "panas", +3: "sangat panas",
}
WORK_HOURS = set(range(8, 19))  # 08:00..18:00 WIB


def temp_to_pmv(temp_c: float) -> int:
    if math.isnan(temp_c): return 0
    if temp_c <= TEMP_BANDS[0]: return -3
    elif temp_c <= TEMP_BANDS[1]: return -2
    elif temp_c <= TEMP_BANDS[2]: return -1
    elif temp_c <= TEMP_BANDS[3]: return 0
    elif temp_c <= TEMP_BANDS[4]: return +1
    elif temp_c <= TEMP_BANDS[5]: return +2
    else: return +3


def pmv_to_ppd(pmv: float) -> float:
    return float(100.0 - 95.0 * math.exp(-0.03353 * (pmv**4) - 0.2179 * (pmv**2)))


def is_working(ts_wib: datetime) -> bool:
    return (ts_wib.weekday() < 5) and (ts_wib.hour in WORK_HOURS)


def energy_kwh_from_env(temp: float, humidity: float, ts_wib: datetime) -> float:
    occ_factor = 1.0 if is_working(ts_wib) else 0.35
    base_load = settings.BASE_LOAD_DAY if is_working(ts_wib) else settings.BASE_LOAD_NIGHT
    ac_work = max(0.0, temp - settings.SETPOINT_C) * settings.AC_COEFF * occ_factor
    humid_penalty = max(0.0, humidity - 60.0) * 0.003 * occ_factor
    noise = np.random.normal(0, 0.05)
    ekwh = base_load + ac_work + humid_penalty + noise
    return float(max(0.05, ekwh))


def day_name_id(ts_wib: datetime) -> str:
    en = ts_wib.strftime("%A")
    map_id = {
        "Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu",
        "Thursday": "Kamis", "Friday": "Jumat", "Saturday": "Sabtu", "Sunday": "Minggu"
    }
    return map_id.get(en, en)


def generate_hour(ts_wib: datetime) -> dict:
    """Synthesize one hourly row, including CO2, latency, uptime."""
    hr = ts_wib.hour

    # --- Temperature (°C)
    diurnal_temp = 2.8 * math.sin(2 * math.pi * (hr - 14) / 24.0)
    temp_base = 25.5 + diurnal_temp
    temp_noise = np.random.normal(0, 0.7)
    temp = float(np.clip(temp_base + temp_noise, 20.0, 33.0))

    # --- Humidity (%)
    hum_base = 65.0 - 0.25 * (temp - 25.5)
    hum_diurnal = 4.0 * math.sin(2 * math.pi * (hr + 2) / 24.0)
    hum_noise = np.random.normal(0, 3.0)
    humidity = float(np.clip(hum_base + hum_diurnal + hum_noise, 40.0, 90.0))

    # --- Wind (m/s)
    wind_diurnal = 1.2 * math.sin(2 * math.pi * (hr - 16) / 24.0)
    wind_base = 2.2 + wind_diurnal
    wind_noise = abs(np.random.normal(0, 0.8))
    wind_speed = float(np.clip(wind_base + wind_noise, 0.0, 12.0))

    # --- PM2.5 (µg/m³)
    pm_base = 12.0 + 1.2 * math.sin(2 * math.pi * (hr - 7) / 24.0)
    pm_noise = abs(np.random.normal(0, 2.0))
    pm25 = float(np.clip(pm_base + pm_noise, 5.0, 120.0))

    # --- NEW: CO2 (ppm)
    # Typical office ~ 420–1200 ppm; higher when occupied
    occ_factor = 1.0 if is_working(ts_wib) else 0.5
    co2_base = 450 + 400 * occ_factor  # 450 idle → 850/1150 occupied
    co2_diurnal = 120 * math.sin(2 * math.pi * (hr - 13) / 24.0)
    co2_noise = np.random.normal(0, 40)
    co2 = float(np.clip(co2_base + co2_diurnal + co2_noise, 380.0, 2000.0))

    # --- Energy (kWh), Cost (IDR), EUI (kWh/m2)
    energy_kwh = energy_kwh_from_env(temp, humidity, ts_wib)
    cost = round(energy_kwh * settings.TARIFF_IDR_PER_KWH, 2)
    eui = float(energy_kwh / settings.FLOOR_AREA_M2)

    # --- PMV / PPD (discrete bands)
    pmv = float(temp_to_pmv(temp))
    ppd = float(np.clip(pmv_to_ppd(pmv), 0.0, 100.0))
    label = PMV_LABELS[int(pmv)]

    # --- NEW: Latency (sec) & Uptime (%)
    # Latency: lower is better; mark >1s as not compliant (FE will compute)
    base_latency = 0.45 if is_working(ts_wib) else 0.6
    latency = float(np.clip(base_latency + abs(np.random.normal(0, 0.2)), 0.05, 3.0))

    # Uptime: near 100%, with tiny dips; monthly target >= 99%
    uptime = float(np.clip(99.8 + np.random.normal(0, 0.08), 95.0, 100.0))

    # Store ts as UTC
    row = {
        "ts": ts_wib.astimezone(timezone.utc),
        "temp": round(temp, 3),
        "humidity": round(humidity, 1),
        "wind_speed": round(wind_speed, 3),
        "pm25": round(pm25, 1),
        "co2": round(co2, 0),

        "latency_sec": round(latency, 3),
        "uptime_pct": round(uptime, 3),
        "energy_kwh": round(energy_kwh, 3),
        "cost_idr": cost,
        
        "eui_kwh_m2": round(eui, 6),
        "pmv": pmv,
        "ppd": round(ppd, 2),
        "pmv_label": label,
        "dayofweek": day_name_id(ts_wib).lower(),
    }
    return row
