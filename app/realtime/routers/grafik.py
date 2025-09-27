from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import psycopg2.extras

from app.core.config import settings
from ..db import get_conn

# Router baru khusus grafik monitoring
router = APIRouter(prefix="/sensor", tags=["Grafik Monitoring"])

WIB = ZoneInfo(settings.APP_TZ)


def _calc_series_window(granularity: str, size: int, ref_wib: datetime):
    """
    Hitung start/end window (WIB) + ekspresi bucket SQL (pakai waktu lokal).
    weekly: dibucket PER HARI (sesuai permintaan).
    """
    if granularity == "hourly":
        end = ref_wib.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        start = end - timedelta(hours=size)
        bucket_sql = "date_trunc('hour', (ts AT TIME ZONE %(tz)s))"
    elif granularity == "daily":
        end = ref_wib.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        start = end - timedelta(days=size)
        bucket_sql = "date_trunc('day', (ts AT TIME ZONE %(tz)s))"
    # elif granularity == "weekly":
    #     # deret HARI dalam jendela mingguan (7 * size hari)
    #     end = ref_wib.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    #     start = end - timedelta(weeks=size)
    #     bucket_sql = "date_trunc('day', (ts AT TIME ZONE %(tz)s))"
    else:  # "monthly"
        # end = first day next month
        end = ref_wib.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = (end.replace(day=28) + timedelta(days=4)).replace(day=1)
        # start ≈ N bulan ke belakang (pakai 31 hari sebagai aproksimasi aman)
        start = end - timedelta(days=31 * size)
        bucket_sql = "date_trunc('month', (ts AT TIME ZONE %(tz)s))"
    return start, end, bucket_sql


def _series_bucket(start_wib: datetime, end_wib: datetime, bucket_sql: str):
    """
    Ambil deret agregat per bucket (jam / hari / bulan) dengan metrik lengkap.
    Filter di UTC agar index ts terpakai, bucket pakai WIB.
    """
    t0_utc = start_wib.astimezone(ZoneInfo("UTC"))
    t1_utc = end_wib.astimezone(ZoneInfo("UTC"))

    sql = f"""
    SELECT
      {bucket_sql} AS bucket,
      AVG(temp)         AS avg_temp,
      AVG(humidity)     AS avg_humidity,
      AVG(wind_speed)   AS avg_wind_speed,
      AVG(pm25)         AS avg_pm25,
      AVG(co2)          AS avg_co2,
      AVG(latency_sec)  AS avg_latency_sec,
      AVG(uptime_pct)   AS avg_uptime_pct,
      AVG(pmv)          AS avg_pmv,
      AVG(ppd)          AS avg_ppd,
      SUM(energy_kwh)   AS total_energy_kwh,
      SUM(cost_idr)     AS total_cost_idr,
      COUNT(*)          AS count
    FROM sensors_hourly
    WHERE ts >= %(t0)s AND ts < %(t1)s
    GROUP BY 1
    ORDER BY 1 ASC;
    """
    params = {"tz": settings.APP_TZ, "t0": t0_utc, "t1": t1_utc}

    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    out = []
    for r in rows:
        bucket = r.pop("bucket")
        # 'bucket' adalah timestamp tanpa tz → beri tz WIB agar ISO konsisten
        r["ts_start"] = bucket.replace(tzinfo=WIB).isoformat()
        total_kwh = float(r.get("total_energy_kwh") or 0.0)
        r["eui_kwh_m2"] = total_kwh / settings.FLOOR_AREA_M2
        out.append(r)
    return out


# ======================== NEW: SERIES ========================

@router.get("/series/daily")
def series_hourly(
    hours: int = Query(24, ge=1, le=24*30, description="Jumlah jam ke belakang"),
    ref_date: str = Query(None, description="YYYY-MM-DD (WIB). Default: sekarang")
):
    try:
        ref = datetime.fromisoformat(ref_date).replace(tzinfo=WIB) if ref_date else datetime.now(tz=WIB)
    except Exception:
        raise HTTPException(status_code=400, detail="ref_date harus YYYY-MM-DD")
    start_wib, end_wib, bucket_sql = _calc_series_window("hourly", hours, ref)
    rows = _series_bucket(start_wib, end_wib, bucket_sql)
    return {
        "granularity": "hourly",
        "start_wib": start_wib.isoformat(),
        "end_wib": end_wib.isoformat(),
        "rows": rows,
        "meta": {
            "tariff_idr_per_kwh": settings.TARIFF_IDR_PER_KWH,
            "floor_area_m2": settings.FLOOR_AREA_M2
        }
    }


@router.get("/series/weekly")
def series_daily(
    days: int = Query(10, ge=1, le=365, description="Jumlah hari ke belakang"),
    ref_date: str = Query(None, description="YYYY-MM-DD (WIB). Default: today")
):
    try:
        ref = datetime.fromisoformat(ref_date).replace(tzinfo=WIB) if ref_date else datetime.now(tz=WIB)
    except Exception:
        raise HTTPException(status_code=400, detail="ref_date harus YYYY-MM-DD")
    start_wib, end_wib, bucket_sql = _calc_series_window("daily", days, ref)
    rows = _series_bucket(start_wib, end_wib, bucket_sql)
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


# @router.get("/series/weekly")
# def series_weekly(
#     weeks: int = Query(2, ge=1, le=52, description="Jumlah minggu ke belakang (dibucket per HARI)"),
#     ref_date: str = Query(None, description="YYYY-MM-DD (WIB). Default: today")
# ):
#     try:
#         ref = datetime.fromisoformat(ref_date).replace(tzinfo=WIB) if ref_date else datetime.now(tz=WIB)
#     except Exception:
#         raise HTTPException(status_code=400, detail="ref_date harus YYYY-MM-DD")
#     start_wib, end_wib, bucket_sql = _calc_series_window("weekly", weeks, ref)
#     rows = _series_bucket(start_wib, end_wib, bucket_sql)
#     return {
#         "granularity": "weekly",  # deret harian dalam jendela mingguan
#         "start_wib": start_wib.isoformat(),
#         "end_wib": end_wib.isoformat(),
#         "rows": rows,
#         "meta": {
#             "tariff_idr_per_kwh": settings.TARIFF_IDR_PER_KWH,
#             "floor_area_m2": settings.FLOOR_AREA_M2
#         }
#     }


@router.get("/series/monthly")
def series_monthly(
    months: int = Query(12, ge=1, le=120, description="Jumlah bulan ke belakang"),
    ref_date: str = Query(None, description="YYYY-MM-DD (WIB). Default: current month")
):
    try:
        ref = datetime.fromisoformat(ref_date).replace(tzinfo=WIB) if ref_date else datetime.now(tz=WIB)
    except Exception:
        raise HTTPException(status_code=400, detail="ref_date harus YYYY-MM-DD")
    start_wib, end_wib, bucket_sql = _calc_series_window("monthly", months, ref)
    rows = _series_bucket(start_wib, end_wib, bucket_sql)
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
