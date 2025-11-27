"""
Forecast endpoints untuk Energy Consumption dan Thermal Comfort (PPV/PPD).
Menggunakan LSTM dan RNN models yang dilatih pada historical data dari sensor_hourly.

Endpoints:
- /realtime/forecast-comfort/daily (24 jam forecast PPV/PPD)
- /realtime/forecast-comfort/weekly (7 hari forecast PPV/PPD)
- /realtime/forecast-comfort/monthly (30 hari forecast PPV/PPD)
- /realtime/forecast-energy/daily (24 jam forecast energy_kwh)
- /realtime/forecast-energy/weekly (7 hari forecast energy_kwh)
- /realtime/forecast-energy/monthly (30 hari forecast energy_kwh)
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

router = APIRouter(prefix="/forecast-comfort", tags=["Forecasting Comfort & Energy"])
energy_router = APIRouter(prefix="/forecast-energy", tags=["Forecasting Comfort & Energy"])

WIB = ZoneInfo(settings.APP_TZ)


# ======================== Helper Functions ========================

def _calc_series_window(granularity: str, size: int, ref_wib: datetime) -> Tuple[datetime, datetime, str]:
    """
    Hitung start/end window (WIB) + ekspresi bucket SQL.
    """
    if granularity == "hourly":
        end = ref_wib.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        start = end - timedelta(hours=size)
        bucket_sql = "date_trunc('hour', (ts AT TIME ZONE %(tz)s))"
    elif granularity == "daily":
        end = ref_wib.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        start = end - timedelta(days=size)
        bucket_sql = "date_trunc('day', (ts AT TIME ZONE %(tz)s))"
    else:
        end = ref_wib.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = (end.replace(day=28) + timedelta(days=4)).replace(day=1)
        start = end - timedelta(days=31 * size)
        bucket_sql = "date_trunc('month', (ts AT TIME ZONE %(tz)s))"
    
    return start, end, bucket_sql


def _series_bucket(start_wib: datetime, end_wib: datetime, bucket_sql: str, metric: str = "energy_kwh") -> np.ndarray:
    """
    Ambil deret agregat per bucket dari database.
    """
    t0_utc = start_wib.astimezone(ZoneInfo("UTC"))
    t1_utc = end_wib.astimezone(ZoneInfo("UTC"))

    metric_col_map = {
        "energy_kwh": "energy_kwh",
        "ppv": "pmv",  # Alias pmv sebagai ppv
        "ppd": "ppd",
    }
    
    if metric not in metric_col_map:
        raise ValueError(f"Unknown metric: {metric}")
    
    col_name = metric_col_map[metric]
    sql = f"""
    SELECT
      {bucket_sql} AS bucket,
      AVG({col_name}) AS metric_value
    FROM sensor_hourly
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
        raise HTTPException(status_code=404, detail=f"Tidak ada data untuk forecast ({metric}). Pastikan sensor_hourly table punya data.")
    
    values = np.array([float(r["metric_value"]) for r in rows])
    return values


def _generate_hourly_timestamps(start_datetime: datetime, hours: int) -> List[str]:
    """Generate list of hourly timestamps."""
    timestamps = []
    current = start_datetime
    for i in range(hours):
        timestamps.append(current.isoformat())
        current += timedelta(hours=1)
    return timestamps


def _generate_daily_timestamps(start_date: datetime, days: int) -> List[str]:
    """Generate list of daily timestamps."""
    timestamps = []
    current = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    for i in range(days):
        timestamps.append(current.date().isoformat())
        current += timedelta(days=1)
    return timestamps


# ======================== PPV/PPD Forecast Endpoints ========================

@router.get("/daily")
def forecast_comfort_daily_endpoint(
    model_type: Literal["lstm", "rnn"] = Query("lstm", description="Model type: lstm atau rnn"),
    target: Literal["ppv", "ppd"] = Query("ppv", description="Target: ppv (Predicted Perception Vote) atau ppd (Percentage Dissatisfied)"),
    hours: int = Query(72, ge=24, le=240, description="Historical hours untuk training (min 24, max 240)"),
    ref_datetime: str = Query(None, description="Reference datetime ISO format (default: sekarang)")
):
    """
    Forecast 24 jam thermal comfort ke depan (PPV atau PPD).
    
    Query params:
    - model_type: "lstm" atau "rnn"
    - target: "ppv" (Predicted Perception Vote) atau "ppd" (Percentage Dissatisfied)
    - hours: jumlah jam historis untuk training (min 24, max 240, recommended 72)
    - ref_datetime: ISO datetime reference (optional, default: sekarang)
    
    Example:
    GET /realtime/forecast-comfort/daily?model_type=lstm&target=ppv&hours=72
    """
    try:
        ref_wib = datetime.fromisoformat(ref_datetime).replace(tzinfo=WIB) if ref_datetime else datetime.now(tz=WIB)
    except Exception:
        raise HTTPException(status_code=400, detail="ref_datetime harus ISO format")
    
    try:
        start, end, bucket_sql = _calc_series_window("hourly", hours, ref_wib)
        historical_vals = _series_bucket(start, end, bucket_sql, metric=target)
        
        if len(historical_vals) < 7:
            raise HTTPException(status_code=400, detail=f"Data tidak cukup (butuh min 7 points, dapat {len(historical_vals)})")
        
        result = forecast_daily(historical_vals, metric=target, model_type=model_type)
        
        forecast_start = ref_wib
        forecast_end = forecast_start + timedelta(hours=24)
        timestamps = _generate_hourly_timestamps(forecast_start, 24)
        
        forecast_with_ts = [
            {"timestamp": ts, "value": float(val)}
            for ts, val in zip(timestamps, result["forecast"])
        ]
        
        result.update({
            "ref_datetime": ref_wib.isoformat(),
            "forecast_start": forecast_start.isoformat(),
            "forecast_end": forecast_end.isoformat(),
            "forecast_with_timestamps": forecast_with_ts,
            "training_datapoints": len(historical_vals),
        })
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weekly")
def forecast_comfort_weekly_endpoint(
    model_type: Literal["lstm", "rnn"] = Query("lstm", description="Model type: lstm atau rnn"),
    target: Literal["ppv", "ppd"] = Query("ppv", description="Target: ppv atau ppd"),
    days: int = Query(90, ge=14, le=90, description="Historical days untuk training (min 14, max 90)"),
    ref_date: str = Query(None, description="Reference date ISO format (default: hari ini)")
):
    """
    Forecast 7 hari thermal comfort ke depan (daily average PPV atau PPD).
    """
    try:
        ref_wib = datetime.fromisoformat(ref_date).replace(tzinfo=WIB) if ref_date else datetime.now(tz=WIB)
    except Exception:
        raise HTTPException(status_code=400, detail="ref_date harus ISO format")
    
    try:
        start, end, bucket_sql = _calc_series_window("daily", days, ref_wib)
        historical_vals = _series_bucket(start, end, bucket_sql, metric=target)
        
        if len(historical_vals) < 7:
            raise HTTPException(status_code=400, detail=f"Data tidak cukup (butuh min 7 points, dapat {len(historical_vals)})")
        
        result = forecast_weekly(historical_vals, metric=target, model_type=model_type)
        
        forecast_start = ref_wib.replace(hour=0, minute=0, second=0, microsecond=0)
        forecast_end = forecast_start + timedelta(days=7)
        timestamps = _generate_daily_timestamps(forecast_start, 7)
        
        forecast_with_ts = [
            {"timestamp": ts, "value": float(val)}
            for ts, val in zip(timestamps, result["forecast"])
        ]
        
        result.update({
            "ref_date": ref_wib.date().isoformat(),
            "forecast_start": forecast_start.date().isoformat(),
            "forecast_end": forecast_end.date().isoformat(),
            "forecast_with_timestamps": forecast_with_ts,
            "training_datapoints": len(historical_vals),
        })
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monthly")
def forecast_comfort_monthly_endpoint(
    model_type: Literal["lstm", "rnn"] = Query("lstm", description="Model type: lstm atau rnn"),
    target: Literal["ppv", "ppd"] = Query("ppv", description="Target: ppv atau ppd"),
    days: int = Query(90, ge=30, le=365, description="Historical days untuk training (min 30, max 365)"),
    ref_date: str = Query(None, description="Reference date ISO format (default: hari ini)")
):
    """
    Forecast 30 hari thermal comfort ke depan (daily average PPV atau PPD).
    """
    try:
        ref_wib = datetime.fromisoformat(ref_date).replace(tzinfo=WIB) if ref_date else datetime.now(tz=WIB)
    except Exception:
        raise HTTPException(status_code=400, detail="ref_date harus ISO format")
    
    try:
        start, end, bucket_sql = _calc_series_window("daily", days, ref_wib)
        historical_vals = _series_bucket(start, end, bucket_sql, metric=target)
        
        if len(historical_vals) < 7:
            raise HTTPException(status_code=400, detail=f"Data tidak cukup (butuh min 7 points, dapat {len(historical_vals)})")
        
        result = forecast_monthly(historical_vals, metric=target, model_type=model_type)
        
        forecast_start = ref_wib.replace(hour=0, minute=0, second=0, microsecond=0)
        forecast_end = forecast_start + timedelta(days=30)
        timestamps = _generate_daily_timestamps(forecast_start, 30)
        
        forecast_with_ts = [
            {"timestamp": ts, "value": float(val)}
            for ts, val in zip(timestamps, result["forecast"])
        ]
        
        result.update({
            "ref_date": ref_wib.date().isoformat(),
            "forecast_start": forecast_start.date().isoformat(),
            "forecast_end": forecast_end.date().isoformat(),
            "forecast_with_timestamps": forecast_with_ts,
            "training_datapoints": len(historical_vals),
        })
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ======================== Energy Forecast Endpoints ========================

@energy_router.get("/daily")
def forecast_energy_daily_endpoint(
    model_type: Literal["lstm", "rnn"] = Query("lstm", description="Model type: lstm atau rnn"),
    hours: int = Query(72, ge=24, le=240, description="Historical hours untuk training"),
    ref_datetime: str = Query(None, description="Reference datetime ISO format (default: sekarang)")
):
    """
    Forecast 24 jam energy consumption (kWh) ke depan.
    
    Example:
    GET /realtime/forecast-energy/daily?model_type=lstm&hours=72
    """
    try:
        ref_wib = datetime.fromisoformat(ref_datetime).replace(tzinfo=WIB) if ref_datetime else datetime.now(tz=WIB)
    except Exception:
        raise HTTPException(status_code=400, detail="ref_datetime harus ISO format")
    
    try:
        start, end, bucket_sql = _calc_series_window("hourly", hours, ref_wib)
        historical_vals = _series_bucket(start, end, bucket_sql, metric="energy_kwh")
        
        if len(historical_vals) < 7:
            raise HTTPException(status_code=400, detail=f"Data tidak cukup (butuh min 7 points, dapat {len(historical_vals)})")
        
        result = forecast_daily(historical_vals, metric="energy_kwh", model_type=model_type)
        
        forecast_start = ref_wib
        forecast_end = forecast_start + timedelta(hours=24)
        timestamps = _generate_hourly_timestamps(forecast_start, 24)
        
        forecast_with_ts = [
            {"timestamp": ts, "value": float(val)}
            for ts, val in zip(timestamps, result["forecast"])
        ]
        
        result.update({
            "ref_datetime": ref_wib.isoformat(),
            "forecast_start": forecast_start.isoformat(),
            "forecast_end": forecast_end.isoformat(),
            "forecast_with_timestamps": forecast_with_ts,
            "training_datapoints": len(historical_vals),
        })
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@energy_router.get("/weekly")
def forecast_energy_weekly_endpoint(
    model_type: Literal["lstm", "rnn"] = Query("lstm", description="Model type: lstm atau rnn"),
    days: int = Query(90, ge=14, le=90, description="Historical days untuk training"),
    ref_date: str = Query(None, description="Reference date ISO format (default: hari ini)")
):
    """
    Forecast 7 hari energy consumption (kWh) ke depan (daily total/average).
    """
    try:
        ref_wib = datetime.fromisoformat(ref_date).replace(tzinfo=WIB) if ref_date else datetime.now(tz=WIB)
    except Exception:
        raise HTTPException(status_code=400, detail="ref_date harus ISO format")
    
    try:
        start, end, bucket_sql = _calc_series_window("daily", days, ref_wib)
        historical_vals = _series_bucket(start, end, bucket_sql, metric="energy_kwh")
        
        if len(historical_vals) < 7:
            raise HTTPException(status_code=400, detail=f"Data tidak cukup (butuh min 7 points, dapat {len(historical_vals)})")
        
        result = forecast_weekly(historical_vals, metric="energy_kwh", model_type=model_type)
        
        forecast_start = ref_wib.replace(hour=0, minute=0, second=0, microsecond=0)
        forecast_end = forecast_start + timedelta(days=7)
        timestamps = _generate_daily_timestamps(forecast_start, 7)
        
        forecast_with_ts = [
            {"timestamp": ts, "value": float(val)}
            for ts, val in zip(timestamps, result["forecast"])
        ]
        
        result.update({
            "ref_date": ref_wib.date().isoformat(),
            "forecast_start": forecast_start.date().isoformat(),
            "forecast_end": forecast_end.date().isoformat(),
            "forecast_with_timestamps": forecast_with_ts,
            "training_datapoints": len(historical_vals),
        })
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@energy_router.get("/monthly")
def forecast_energy_monthly_endpoint(
    model_type: Literal["lstm", "rnn"] = Query("lstm", description="Model type: lstm atau rnn"),
    days: int = Query(90, ge=30, le=365, description="Historical days untuk training"),
    ref_date: str = Query(None, description="Reference date ISO format (default: hari ini)")
):
    """
    Forecast 30 hari energy consumption (kWh) ke depan (daily total/average).
    """
    try:
        ref_wib = datetime.fromisoformat(ref_date).replace(tzinfo=WIB) if ref_date else datetime.now(tz=WIB)
    except Exception:
        raise HTTPException(status_code=400, detail="ref_date harus ISO format")
    
    try:
        start, end, bucket_sql = _calc_series_window("daily", days, ref_wib)
        historical_vals = _series_bucket(start, end, bucket_sql, metric="energy_kwh")
        
        if len(historical_vals) < 7:
            raise HTTPException(status_code=400, detail=f"Data tidak cukup (butuh min 7 points, dapat {len(historical_vals)})")
        
        result = forecast_monthly(historical_vals, metric="energy_kwh", model_type=model_type)
        
        forecast_start = ref_wib.replace(hour=0, minute=0, second=0, microsecond=0)
        forecast_end = forecast_start + timedelta(days=30)
        timestamps = _generate_daily_timestamps(forecast_start, 30)
        
        forecast_with_ts = [
            {"timestamp": ts, "value": float(val)}
            for ts, val in zip(timestamps, result["forecast"])
        ]
        
        result.update({
            "ref_date": ref_wib.date().isoformat(),
            "forecast_start": forecast_start.date().isoformat(),
            "forecast_end": forecast_end.date().isoformat(),
            "forecast_with_timestamps": forecast_with_ts,
            "training_datapoints": len(historical_vals),
        })
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
