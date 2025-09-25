from datetime import datetime, timedelta, timezone
import psycopg2.extras
from app.core.config import settings
from .db import get_conn


def _range_daily(ref_wib: datetime):
    start = ref_wib.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end


def _range_weekly(ref_wib: datetime):
    end = ref_wib.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    start = end - timedelta(days=7)
    return start, end


def _range_monthly(ref_wib: datetime):
    start = ref_wib.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def _summary_query(start_wib: datetime, end_wib: datetime):
    t0_utc = start_wib.astimezone(timezone.utc)
    t1_utc = end_wib.astimezone(timezone.utc)

    sql = """
    WITH cte_win AS (
      SELECT ts, energy_kwh, cost_idr, pmv, ppd
      FROM sensors_hourly
      WHERE ts >= %(t0)s AND ts < %(t1)s
    ),
    cte_agg AS (
      SELECT
        COALESCE(SUM(energy_kwh), 0) AS total_kwh,
        COALESCE(SUM(cost_idr), 0)   AS total_cost_idr,
        COALESCE(AVG(pmv), 0)        AS avg_pmv,
        COALESCE(AVG(ppd), 0)        AS avg_ppd
      FROM cte_win
    ),
    cte_per_hour AS (
      SELECT EXTRACT(HOUR FROM (ts AT TIME ZONE %(tz)s))::INT AS hour_of_day,
             AVG(energy_kwh) AS avg_energy_kwh
      FROM cte_win
      GROUP BY 1
      ORDER BY 1
    )
    SELECT
      (SELECT total_kwh FROM cte_agg) AS total_kwh,
      (SELECT total_cost_idr FROM cte_agg) AS total_cost_idr,
      (SELECT avg_pmv FROM cte_agg) AS avg_pmv,
      (SELECT avg_ppd FROM cte_agg) AS avg_ppd,
      COALESCE(
        (SELECT JSON_AGG(JSON_BUILD_OBJECT('hour', hour_of_day, 'avg_energy_kwh', avg_energy_kwh))
           FROM cte_per_hour),
        '[]'::json
      ) AS hourly_avg;
    """
    params = {"t0": t0_utc, "t1": t1_utc, "tz": settings.APP_TZ}

    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        row = cur.fetchone() or {}

    total_kwh = float(row.get("total_kwh") or 0.0)
    row["total_eui_kwh_m2"] = total_kwh / settings.FLOOR_AREA_M2
    return row


# =========================
# Time-series aggregations
# =========================

def _month_start(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

def _add_months(dt: datetime, months: int) -> datetime:
    # Pure-python month shift (start-of-month)
    y = dt.year + (dt.month - 1 + months) // 12
    m = (dt.month - 1 + months) % 12 + 1
    return dt.replace(year=y, month=m, day=1, hour=0, minute=0, second=0, microsecond=0)


def series_query(bucket: str, start_wib: datetime, end_wib: datetime):
    """
    Deret waktu agregasi berdasarkan 'bucket' ∈ {'day','week','month'} pada zona waktu lokal.
    Menghasilkan list ascending berdasarkan waktu bucket.
    """
    if bucket not in {"day", "week", "month"}:
        raise ValueError("bucket harus 'day', 'week', atau 'month'.")

    t0_utc = start_wib.astimezone(timezone.utc)
    t1_utc = end_wib.astimezone(timezone.utc)

    sql = """
    SELECT
      date_trunc(%(bucket)s, (ts AT TIME ZONE %(tz)s)) AS bucket_start_wib,
      AVG(temp)        AS avg_temp,
      AVG(humidity)    AS avg_humidity,
      AVG(wind_speed)  AS avg_wind_speed,
      AVG(pm25)        AS avg_pm25,
      SUM(energy_kwh)  AS total_energy_kwh,
      SUM(cost_idr)    AS total_cost_idr,
      AVG(pmv)         AS avg_pmv,
      AVG(ppd)         AS avg_ppd,
      COUNT(*)         AS n
    FROM sensors_hourly
    WHERE ts >= %(t0)s AND ts < %(t1)s
    GROUP BY 1
    ORDER BY 1 ASC;
    """
    params = {
        "bucket": bucket,
        "tz": settings.APP_TZ,
        "t0": t0_utc,
        "t1": t1_utc,
    }

    rows_out = []
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall() or []

    from zoneinfo import ZoneInfo
    WIB = ZoneInfo(settings.APP_TZ)

    for r in rows:
        # date_trunc(...) atas "timestamp without time zone" → naive; tambahkan tz info WIB
        ts_local = r.pop("bucket_start_wib")
        ts_iso = ts_local.replace(tzinfo=WIB).isoformat()

        total_kwh = float(r.get("total_energy_kwh") or 0.0)
        r = {
            "ts_start": ts_iso,
            "avg_temp": float(r.get("avg_temp") or 0.0),
            "avg_humidity": float(r.get("avg_humidity") or 0.0),
            "avg_wind_speed": float(r.get("avg_wind_speed") or 0.0),
            "avg_pm25": float(r.get("avg_pm25") or 0.0),
            "total_energy_kwh": total_kwh,
            "total_cost_idr": float(r.get("total_cost_idr") or 0.0),
            "avg_pmv": float(r.get("avg_pmv") or 0.0),
            "avg_ppd": float(r.get("avg_ppd") or 0.0),
            "eui_kwh_m2": total_kwh / settings.FLOOR_AREA_M2,
            "count": int(r.get("n") or 0),
        }
        rows_out.append(r)

    return rows_out


def series_range_daily(ref_wib: datetime, days: int):
    end = ref_wib.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    start = end - timedelta(days=days)
    return start, end


def series_range_weekly(ref_wib: datetime, weeks: int):
    end = ref_wib.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    start = end - timedelta(weeks=weeks)
    return start, end


def series_range_monthly(ref_wib: datetime, months: int):
    ref_month0 = _month_start(ref_wib)
    start = _add_months(ref_month0, -months + 1)
    end = _add_months(ref_month0, 1)
    return start, end
