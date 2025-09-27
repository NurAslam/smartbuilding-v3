from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import psycopg2.extras

from typing import Literal

from app.realtime.scheduler import scheduler

from app.core.config import settings
from ..db import get_conn, init_table, insert_row
from ..generator import generate_hour
from ..summaries import (
    _summary_query,
)

router = APIRouter(prefix="/sensor", tags=["Laporan"])
WIB = ZoneInfo(settings.APP_TZ)

APP_VERSION = "1.1.0"


@router.get("/status")
def status():
    return {"status": "ok"}

# @router.get("/scheduler-status")
# def scheduler_status():
#     jobs = []
#     for j in scheduler.get_jobs():
#         jobs.append({
#             "id": j.id,
#             "next_run_time": j.next_run_time.isoformat() if j.next_run_time else None,
#         })
#     return {
#         "running": scheduler.running,
#         "tz": settings.APP_TZ,
#         "now_wib": datetime.now(tz=WIB).isoformat(),
#         "jobs": jobs,
#     }


# @router.post("/generate-now")
# def generate_now():
#     ts_now = datetime.now(tz=WIB)
#     ts_hour = ts_now.replace(minute=0, second=0, microsecond=0)
#     row = generate_hour(ts_hour)
#     insert_row(row)
#     row_view = row.copy()
#     row_view["ts"] = ts_hour.isoformat()
#     return {"status": "ok", "row": row_view}


@router.get("/latest")
def latest(n: int = Query(50, ge=1, le=1000)):
    sql = """
    SELECT (ts AT TIME ZONE %s) AS ts_local,
           temp, humidity, wind_speed, pm25, co2, latency_sec, uptime_pct,
           energy_kwh, cost_idr, eui_kwh_m2, pmv, ppd, pmv_label, dayofweek
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
        # FE can check: r["latency_sec"] > 1.0 ? "not compliant" : "compliant"
        out.append(r)
    return {"rows": out}


@router.get("/summary/daily")
def summary_daily(ref_date: str = Query(None, )):
    try:
        ref = datetime.fromisoformat(ref_date).replace(tzinfo=WIB) if ref_date else datetime.now(tz=WIB)
    except Exception:
        raise HTTPException(status_code=400, detail="ref_date harus YYYY-MM-DD")

    start_wib = ref.replace(hour=0, minute=0, second=0, microsecond=0)
    end_wib   = start_wib + timedelta(days=1)

    data = _summary_query(start_wib, end_wib)
    data.update({
        "start_wib": start_wib.isoformat(),
        "end_wib": end_wib.isoformat(),
        "granularity": "daily",
        "tariff_idr_per_kwh": settings.TARIFF_IDR_PER_KWH,
        "floor_area_m2": settings.FLOOR_AREA_M2
    })
    return data


@router.get("/summary/weekly")
def summary_weekly(ref_date: str = Query(None,)):
    try:
        ref = datetime.fromisoformat(ref_date).replace(tzinfo=WIB) if ref_date else datetime.now(tz=WIB)
    except Exception:
        raise HTTPException(status_code=400, detail="ref_date harus YYYY-MM-DD")
    end_wib   = ref.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    start_wib = end_wib - timedelta(days=7)

    data = _summary_query(start_wib, end_wib)
    data.update({
        "start_wib": start_wib.isoformat(),
        "end_wib": end_wib.isoformat(),
        "tariff_idr_per_kwh": settings.TARIFF_IDR_PER_KWH,
        "floor_area_m2": settings.FLOOR_AREA_M2,
        "granularity": "weekly"
    })
    return data

@router.get("/summary/monthly")
def summary_monthly(ref_date: str = Query(None)):
    try:
        ref = datetime.fromisoformat(ref_date).replace(tzinfo=WIB) if ref_date else datetime.now(tz=WIB)
    except Exception:
        raise HTTPException(status_code=400, detail="ref_date harus YYYY-MM-DD")
    start_wib = ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # first day next month:
    end_wib   = (start_wib.replace(day=28) + timedelta(days=4)).replace(day=1)

    data = _summary_query(start_wib, end_wib)
    data.update({
        "start_wib": start_wib.isoformat(),
        "end_wib": end_wib.isoformat(),
        "tariff_idr_per_kwh": settings.TARIFF_IDR_PER_KWH,
        "floor_area_m2": settings.FLOOR_AREA_M2,
        "granularity": "monthly"
    })
    return data
