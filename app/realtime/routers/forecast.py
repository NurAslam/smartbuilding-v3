"""
Forecasting endpoints untuk daily, weekly, dan monthly forecasts.
Menggunakan LSTM dan RNN models dari domain.forecast.
Data source: sensors_hourly (sama seperti grafik monitoring)
Automatic update: Model otomatis dilatih ulang setiap ada data baru dari database
"""

from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List, Literal, Tuple
import numpy as np

from app.core.config import settings
from ..db import get_conn
from ..domain.forecast import forecast_daily, forecast_weekly, forecast_monthly
import psycopg2.extras

router = APIRouter(prefix="/forecast", tags=["Forecasting"])
WIB = ZoneInfo(settings.APP_TZ)


# ======================== Helper Functions (Same as Grafik Monitoring) ========================

def _calc_series_window(granularity: str, size: int, ref_wib: datetime) -> Tuple[datetime, datetime, str]:
    """
    Hitung start/end window (WIB) + ekspresi bucket SQL.
    Sesuai dengan struktur grafik.py untuk konsistensi data.
    
    Args:
        granularity: "hourly" (untuk daily forecast) atau "daily" (untuk weekly/monthly)
        size: jumlah unit historis (jam atau hari)
        ref_wib: reference datetime (WIB)
    """
    if granularity == "hourly":
        # Untuk daily forecast: ambil jam-jaman historis
        end = ref_wib.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        start = end - timedelta(hours=size)
        bucket_sql = "date_trunc('hour', (ts AT TIME ZONE %(tz)s))"
    elif granularity == "daily":
        # Untuk weekly/monthly forecast: ambil hari-hari historis
        # Include full current day: end = besok 00:00 (UTC)
        end = ref_wib.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        start = end - timedelta(days=size)
        bucket_sql = "date_trunc('day', (ts AT TIME ZONE %(tz)s))"
    else:  # "monthly"
        # Untuk monthly (tidak dipakai sekarang)
        end = ref_wib.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = (end.replace(day=28) + timedelta(days=4)).replace(day=1)
        start = end - timedelta(days=31 * size)
        bucket_sql = "date_trunc('month', (ts AT TIME ZONE %(tz)s))"
    
    return start, end, bucket_sql


def _series_bucket(start_wib: datetime, end_wib: datetime, bucket_sql: str, metric: str = "temp") -> np.ndarray:
    """
    Ambil deret agregat per bucket dari database (sama seperti grafik monitoring).
    Filter menggunakan UTC agar index ts terpakai, bucket pakai WIB.
    
    Args:
        start_wib, end_wib: window time (WIB)
        bucket_sql: SQL expression untuk bucketing
        metric: "temp", "humidity", "wind_speed", "pm25", "co2"
        
    Returns:
        numpy array dari aggregated values
    """
    t0_utc = start_wib.astimezone(ZoneInfo("UTC"))
    t1_utc = end_wib.astimezone(ZoneInfo("UTC"))

    metric_col_map = {
        "temp": "temp",
        "humidity": "humidity",
        "wind_speed": "wind_speed",
        "pm25": "pm25",
        "co2": "co2",
    }
    
    if metric not in metric_col_map:
        raise ValueError(f"Unknown metric: {metric}")
    
    col_name = metric_col_map[metric]
    sql = f"""
    SELECT
      {bucket_sql} AS bucket,
      AVG({col_name}) AS metric_value
    FROM sensors_hourly
    WHERE ts >= %(t0)s AND ts < %(t1)s
    GROUP BY 1
    ORDER BY 1 ASC;
    """
    params = {"tz": settings.APP_TZ, "t0": t0_utc, "t1": t1_utc}

    try:
        with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    if not rows:
        raise HTTPException(status_code=404, detail=f"Tidak ada data untuk forecast ({metric}). Pastikan sensors_hourly table punya data.")
    
    values = np.array([float(r["metric_value"]) for r in rows])
    return values


# ======================== Timestamp Generators ========================

def _generate_hourly_timestamps(start_datetime: datetime, hours: int) -> List[str]:
    """Generate list of hourly timestamps starting from start_datetime."""
    timestamps = []
    current = start_datetime
    for i in range(hours):
        timestamps.append(current.isoformat())
        current += timedelta(hours=1)
    return timestamps


def _generate_daily_timestamps(start_date: datetime, days: int) -> List[str]:
    """Generate list of daily timestamps starting from start_date."""
    timestamps = []
    current = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    for i in range(days):
        timestamps.append(current.date().isoformat())
        current += timedelta(days=1)
    return timestamps



@router.get("/daily")
def forecast_daily_endpoint(
    model_type: Literal["lstm", "rnn"] = Query("lstm", description="Model type: lstm atau rnn"),
    metric: str = Query("temp", description="Metric: temp, humidity, wind_speed, pm25, co2"),
    hours: int = Query(72, ge=24, le=240, description="Historical hours untuk training (min 24, max 240)"),
    ref_datetime: str = Query(None, description="Reference datetime ISO format (default: sekarang)")
):
    """
    Forecast 24 jam ke depan dari hourly historical data (dari database).
    Data automatically updated dari sensors_hourly.
    
    Query params:
    - model_type: "lstm" atau "rnn"
    - metric: "temp", "humidity", "wind_speed", "pm25", "co2"
    - hours: jumlah jam historis untuk training (min 24, recommended 72)
    - ref_datetime: ISO datetime reference (optional, default: sekarang)
    
    Example:
    GET /realtime/forecast/daily?model_type=lstm&metric=temp&hours=72
    
    Returns:
    {
        "granularity": "daily",
        "metric": "temp",
        "forecast_hours": 24,
        "forecast": [23.5, 23.8, 24.1, ...],
        "model_used": "LSTM",
        "ref_datetime": "2025-11-27T15:30:00+07:00",
        "forecast_start": "2025-11-27T15:30:00+07:00",
        "forecast_end": "2025-11-28T15:30:00+07:00",
        "training_datapoints": 72
    }
    """
    try:
        ref_wib = datetime.fromisoformat(ref_datetime).replace(tzinfo=WIB) if ref_datetime else datetime.now(tz=WIB)
    except Exception:
        raise HTTPException(status_code=400, detail="ref_datetime harus ISO format (YYYY-MM-DDTHH:MM:SS)")
    
    try:
        # Get historical hourly data (dari database, sama seperti grafik monitoring)
        start, end, bucket_sql = _calc_series_window("hourly", hours, ref_wib)
        hourly_vals = _series_bucket(start, end, bucket_sql, metric=metric)
        
        if len(hourly_vals) < 7:
            raise HTTPException(status_code=400, detail=f"Data tidak cukup (butuh min 7 points, dapat {len(hourly_vals)})")
        
        # Forecast dengan model (otomatis cache/retrain)
        result = forecast_daily(hourly_vals, metric=metric, model_type=model_type)
        
        # Add timestamps
        forecast_start = ref_wib
        forecast_end = forecast_start + timedelta(hours=24)
        timestamps = _generate_hourly_timestamps(forecast_start, 24)
        
        # Create forecast with timestamps
        forecast_with_ts = [
            {"timestamp": ts, "value": float(val)}
            for ts, val in zip(timestamps, result["forecast"])
        ]
        
        result.update({
            "ref_datetime": ref_wib.isoformat(),
            "forecast_start": forecast_start.isoformat(),
            "forecast_end": forecast_end.isoformat(),
            "forecast_with_timestamps": forecast_with_ts,
            "training_datapoints": len(hourly_vals),
        })
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecast error: {str(e)}")


@router.get("/weekly")
def forecast_weekly_endpoint(
    model_type: Literal["lstm", "rnn"] = Query("lstm", description="Model type: lstm atau rnn"),
    metric: str = Query("temp", description="Metric: temp, humidity, wind_speed, pm25, co2"),
    days: int = Query(90, ge=14, le=90, description="Historical days untuk training (min 14, max 90)"),
    ref_date: str = Query(None, description="Reference date ISO format (default: hari ini)")
):
    """
    Forecast 7 hari ke depan dari daily aggregated data (dari database).
    Data automatically updated setiap hari baru tersedia.
    
    Query params:
    - model_type: "lstm" atau "rnn"
    - metric: "temp", "humidity", "wind_speed", "pm25", "co2"
    - days: jumlah hari historis untuk training (min 14, recommended 30)
    - ref_date: ISO date reference (optional, default: hari ini)
    
    Example:
    GET /realtime/forecast/weekly?model_type=lstm&metric=temp&days=30
    
    Returns:
    {
        "granularity": "weekly",
        "metric": "temp",
        "forecast_days": 7,
        "forecast": [25.3, 24.8, 23.9, 22.5, 21.8, 22.3, 23.5],
        "model_used": "LSTM",
        "ref_date": "2025-11-27",
        "forecast_start": "2025-11-27",
        "forecast_end": "2025-12-04",
        "forecast_days_labels": ["Thursday", "Friday", "Saturday", "Sunday", "Monday", "Tuesday", "Wednesday"],
        "training_datapoints": 30
    }
    """
    try:
        if ref_date:
            ref_wib = datetime.fromisoformat(ref_date).replace(tzinfo=WIB)
        else:
            ref_wib = datetime.now(tz=WIB)
    except Exception:
        raise HTTPException(status_code=400, detail="ref_date harus ISO format (YYYY-MM-DD)")
    
    try:
        # Get historical daily data (dari database) - sama logic dengan monthly
        start, end, bucket_sql = _calc_series_window("daily", days, ref_wib)
        daily_vals = _series_bucket(start, end, bucket_sql, metric=metric)
        
        if len(daily_vals) < 7:
            raise HTTPException(status_code=400, detail=f"Data tidak cukup (butuh min 7 points, dapat {len(daily_vals)})")
        
        # Forecast
        result = forecast_weekly(daily_vals, metric=metric, model_type=model_type)
        
        # Add timestamps and metadata
        forecast_start = ref_wib.replace(hour=0, minute=0, second=0, microsecond=0)
        forecast_end = forecast_start + timedelta(days=7)
        timestamps = _generate_daily_timestamps(forecast_start, 7)
        
        # Create forecast with timestamps
        forecast_with_ts = [
            {"timestamp": ts, "value": float(val)}
            for ts, val in zip(timestamps, result["forecast"])
        ]
        
        result.update({
            "ref_date": ref_wib.date().isoformat(),
            "forecast_start": forecast_start.date().isoformat(),
            "forecast_end": forecast_end.date().isoformat(),
            "forecast_with_timestamps": forecast_with_ts,
            "training_datapoints": len(daily_vals),
        })
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecast error: {str(e)}")


@router.get("/monthly")
def forecast_monthly_endpoint(
    model_type: Literal["lstm", "rnn"] = Query("lstm", description="Model type: lstm atau rnn"),
    metric: str = Query("temp", description="Metric: temp, humidity, wind_speed, pm25, co2"),
    days: int = Query(90, ge=30, le=365, description="Historical days untuk training (min 30, max 365)"),
    ref_date: str = Query(None, description="Reference date ISO format (default: hari ini)")
):
    """
    Forecast 30 hari ke depan dari daily aggregated data (dari database).
    Data automatically updated setiap hari baru tersedia di database.
    
    Query params:
    - model_type: "lstm" atau "rnn"
    - metric: "temp", "humidity", "wind_speed", "pm25", "co2"
    - days: jumlah hari historis untuk training (min 30, recommended 90)
    - ref_date: ISO date reference (optional, default: hari ini)
    
    Example:
    GET /realtime/forecast/monthly?model_type=lstm&metric=temp&days=90
    
    Returns:
    {
        "granularity": "monthly",
        "metric": "temp",
        "forecast_days": 30,
        "forecast": [25.3, 24.8, 23.9, ..., 26.1],
        "model_used": "LSTM",
        "ref_date": "2025-11-27",
        "forecast_start": "2025-11-27",
        "forecast_end": "2025-12-27",
        "training_datapoints": 90
    }
    """
    try:
        if ref_date:
            ref_wib = datetime.fromisoformat(ref_date).replace(tzinfo=WIB)
        else:
            ref_wib = datetime.now(tz=WIB)
    except Exception:
        raise HTTPException(status_code=400, detail="ref_date harus ISO format (YYYY-MM-DD)")
    
    try:
        # Get historical daily data (dari database)
        start, end, bucket_sql = _calc_series_window("daily", days, ref_wib)
        daily_vals = _series_bucket(start, end, bucket_sql, metric=metric)
        
        if len(daily_vals) < 7:
            raise HTTPException(status_code=400, detail=f"Data tidak cukup (butuh min 7 points, dapat {len(daily_vals)})")
        
        # Forecast
        result = forecast_monthly(daily_vals, metric=metric, model_type=model_type)
        
        # Add timestamps
        forecast_start = ref_wib.replace(hour=0, minute=0, second=0, microsecond=0)
        forecast_end = forecast_start + timedelta(days=30)
        timestamps = _generate_daily_timestamps(forecast_start, 30)
        
        # Create forecast with timestamps
        forecast_with_ts = [
            {"timestamp": ts, "value": float(val)}
            for ts, val in zip(timestamps, result["forecast"])
        ]
        
        result.update({
            "ref_date": ref_wib.date().isoformat(),
            "forecast_start": forecast_start.date().isoformat(),
            "forecast_end": forecast_end.date().isoformat(),
            "forecast_with_timestamps": forecast_with_ts,
            "training_datapoints": len(daily_vals),
        })
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecast error: {str(e)}")
