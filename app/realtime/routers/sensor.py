from fastapi import APIRouter, Query, HTTPException
from datetime import datetime
from zoneinfo import ZoneInfo
import psycopg2.extras

from app.realtime.scheduler import scheduler

from app.core.config import settings
from ..db import get_conn, init_table, insert_row
from ..generator import generate_hour
from ..summaries import (
    _range_daily, _range_weekly, _range_monthly, _summary_query,
    series_query, series_range_daily, series_range_weekly, series_range_monthly
)

router = APIRouter(prefix="/sensor", tags=["sensor"])
WIB = ZoneInfo(settings.APP_TZ)

APP_VERSION = "1.1.0"


@router.get("/status")
def status():
    return {"status": "ok", "version": APP_VERSION, "tz": settings.APP_TZ, "floor_area_m2": settings.FLOOR_AREA_M2}

@router.get("/scheduler-status")
def scheduler_status():
    jobs = []
    for j in scheduler.get_jobs():
        jobs.append({
            "id": j.id,
            "next_run_time": j.next_run_time.isoformat() if j.next_run_time else None,
        })
    return {
        "running": scheduler.running,
        "tz": settings.APP_TZ,
        "now_wib": datetime.now(tz=WIB).isoformat(),
        "jobs": jobs,
    }


@router.post("/generate-now")
def generate_now():
    ts_now = datetime.now(tz=WIB)
    ts_hour = ts_now.replace(minute=0, second=0, microsecond=0)
    row = generate_hour(ts_hour)
    insert_row(row)
    row_view = row.copy()
    row_view["ts"] = ts_hour.isoformat()
    return {"status": "ok", "row": row_view}


@router.get("/latest")
def latest(n: int = Query(50, ge=1, le=1000)):
    sql = """
    SELECT (ts AT TIME ZONE %s) AS ts_local,
           temp, humidity, wind_speed, pm25, energy_kwh, cost_idr, eui_kwh_m2,
           pmv, ppd, pmv_label, dayofweek
    FROM sensors_hourly
    ORDER BY ts DESC
    LIMIT %s;
    """
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (settings.APP_TZ, n))
        rows = cur.fetchall()
    out = []
    for r in rows:
        ts_local = r.pop("ts_local")
        r["ts_wib"] = ts_local.replace(tzinfo=WIB).isoformat()
        out.append(r)
    return {"rows": out}


# =========================
# Summary endpoints (existing)
# =========================

@router.get("/summary/daily")
def summary_daily(ref_date: str = Query(None, description="YYYY-MM-DD (WIB). Default: today")):
    try:
        ref = datetime.fromisoformat(ref_date).replace(tzinfo=WIB) if ref_date else datetime.now(tz=WIB)
    except Exception:
        raise HTTPException(status_code=400, detail="ref_date harus YYYY-MM-DD")
    start_wib, end_wib = _range_daily(ref)
    data = _summary_query(start_wib, end_wib)
    data.update({
        "start_wib": start_wib.isoformat(),
        "end_wib": end_wib.isoformat(),
        "tariff_idr_per_kwh": settings.TARIFF_IDR_PER_KWH,
        "floor_area_m2": settings.FLOOR_AREA_M2
    })
    return data


@router.get("/summary/weekly")
def summary_weekly(ref_date: str = Query(None, description="YYYY-MM-DD (WIB). Default: today")):
    try:
        ref = datetime.fromisoformat(ref_date).replace(tzinfo=WIB) if ref_date else datetime.now(tz=WIB)
    except Exception:
        raise HTTPException(status_code=400, detail="ref_date harus YYYY-MM-DD")
    start_wib, end_wib = _range_weekly(ref)
    data = _summary_query(start_wib, end_wib)
    data.update({
        "start_wib": start_wib.isoformat(),
        "end_wib": end_wib.isoformat(),
        "tariff_idr_per_kwh": settings.TARIFF_IDR_PER_KWH,
        "floor_area_m2": settings.FLOOR_AREA_M2
    })
    return data


@router.get("/summary/monthly")
def summary_monthly(ref_date: str = Query(None, description="YYYY-MM-DD (WIB). Default: current month")):
    try:
        ref = datetime.fromisoformat(ref_date).replace(tzinfo=WIB) if ref_date else datetime.now(tz=WIB)
    except Exception:
        raise HTTPException(status_code=400, detail="ref_date harus YYYY-MM-DD")
    start_wib, end_wib = _range_monthly(ref)
    data = _summary_query(start_wib, end_wib)
    data.update({
        "start_wib": start_wib.isoformat(),
        "end_wib": end_wib.isoformat(),
        "tariff_idr_per_kwh": settings.TARIFF_IDR_PER_KWH,
        "floor_area_m2": settings.FLOOR_AREA_M2
    })
    return data


# =========================
# NEW: Time-series endpoints for charts
# =========================

@router.get("/series/daily")
def series_daily(
    days: int = Query(30, ge=1, le=365, description="Jumlah hari ke belakang"),
    ref_date: str = Query(None, description="YYYY-MM-DD (WIB). Default: today")
):
    """Deret waktu agregasi per-hari (bucket = day). Cocok untuk line chart harian."""
    try:
        ref = datetime.fromisoformat(ref_date).replace(tzinfo=WIB) if ref_date else datetime.now(tz=WIB)
    except Exception:
        raise HTTPException(status_code=400, detail="ref_date harus YYYY-MM-DD")
    start_wib, end_wib = series_range_daily(ref, days)
    rows = series_query("day", start_wib, end_wib)
    return {
        "granularity": "daily",
        "start_wib": start_wib.isoformat(),
        "end_wib": end_wib.isoformat(),
        "rows": rows,
        "meta": {
            "tariff_idr_per_kwh": settings.TARIFF_IDR_PER_KWH,
            "floor_area_m2": settings.FLOOR_AREA_M2
        }
    }


@router.get("/series/weekly")
def series_weekly(
    weeks: int = Query(12, ge=1, le=260, description="Jumlah minggu ke belakang"),
    ref_date: str = Query(None, description="YYYY-MM-DD (WIB). Default: today")
):
    """Deret waktu agregasi per-minggu (bucket = week)."""
    try:
        ref = datetime.fromisoformat(ref_date).replace(tzinfo=WIB) if ref_date else datetime.now(tz=WIB)
    except Exception:
        raise HTTPException(status_code=400, detail="ref_date harus YYYY-MM-DD")
    start_wib, end_wib = series_range_weekly(ref, weeks)
    rows = series_query("week", start_wib, end_wib)
    return {
        "granularity": "weekly",
        "start_wib": start_wib.isoformat(),
        "end_wib": end_wib.isoformat(),
        "rows": rows,
        "meta": {
            "tariff_idr_per_kwh": settings.TARIFF_IDR_PER_KWH,
            "floor_area_m2": settings.FLOOR_AREA_M2
        }
    }


@router.get("/series/monthly")
def series_monthly(
    months: int = Query(12, ge=1, le=120, description="Jumlah bulan ke belakang"),
    ref_date: str = Query(None, description="YYYY-MM-DD (WIB). Default: current month")
):
    """Deret waktu agregasi per-bulan (bucket = month)."""
    try:
        ref = datetime.fromisoformat(ref_date).replace(tzinfo=WIB) if ref_date else datetime.now(tz=WIB)
    except Exception:
        raise HTTPException(status_code=400, detail="ref_date harus YYYY-MM-DD")
    start_wib, end_wib = series_range_monthly(ref, months)
    rows = series_query("month", start_wib, end_wib)
    return {
        "granularity": "monthly",
        "start_wib": start_wib.isoformat(),
        "end_wib": end_wib.isoformat(),
        "rows": rows,
        "meta": {
            "tariff_idr_per_kwh": settings.TARIFF_IDR_PER_KWH,
            "floor_area_m2": settings.FLOOR_AREA_M2
        }
    }
