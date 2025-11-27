import psycopg2
import psycopg2.extras
from app.core.config import settings


def get_conn():
    return psycopg2.connect(
        host=settings.DB_HOST, port=settings.DB_PORT, dbname=settings.DB_NAME,
        user=settings.DB_USER, password=settings.DB_PASS
    )


def init_table():
    ddl = """
    CREATE TABLE IF NOT EXISTS sensor_hourly (
        id BIGSERIAL PRIMARY KEY,
        ts TIMESTAMPTZ NOT NULL UNIQUE,      -- UTC
        temp REAL NOT NULL,
        humidity REAL NOT NULL,
        wind_speed REAL NOT NULL,
        pm25 REAL NOT NULL,

        co2_ppm REAL NOT NULL DEFAULT 450,
        latency_ms INTEGER NOT NULL DEFAULT 300,
        latency_ok BOOLEAN NOT NULL DEFAULT TRUE,
        uptime_ok BOOLEAN NOT NULL DEFAULT FALSE,
        recovery_sec INTEGER NOT NULL DEFAULT 0,
        recovery_ok BOOLEAN NOT NULL DEFAULT TRUE,


        energy_kwh REAL NOT NULL,
        cost_idr NUMERIC(18,2) NOT NULL,
        eui_kwh_m2 REAL NOT NULL,

        pmv REAL NOT NULL CHECK (pmv BETWEEN -3 AND 3),
        ppd REAL NOT NULL CHECK (ppd BETWEEN 0 AND 100),
        pmv_label TEXT NOT NULL,
        dayofweek TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_sensor_hourly_ts_desc ON sensor_hourly (ts DESC);
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(ddl)


def insert_row(row: dict):
    """
    Insert a row into sensor_hourly table.
    Handles column name transformations between generator output and DB schema.
    """
    # Transform row dict to match table schema
    transformed_row = {
        "ts": row.get("ts"),
        "temp": row.get("temp"),
        "humidity": row.get("humidity"),
        "wind_speed": row.get("wind_speed"),
        "pm25": row.get("pm25"),
        "co2_ppm": row.get("co2"),  # Map generator's "co2" to table's "co2_ppm"
        "latency_ms": int(row.get("latency_sec", 0) * 1000),  # Convert seconds to milliseconds
        "latency_ok": row.get("latency_sec", 0) * 1000 <= 1000,  # OK if <= 1000ms
        "uptime_ok": row.get("uptime_pct", 0) >= 99.0,  # OK if >= 99%
        "recovery_sec": 0,  # Default
        "recovery_ok": True,  # Default
        "energy_kwh": row.get("energy_kwh"),
        "cost_idr": row.get("cost_idr"),
        "eui_kwh_m2": row.get("eui_kwh_m2"),
        "pmv": row.get("pmv"),
        "ppd": row.get("ppd"),
        "pmv_label": row.get("pmv_label"),
        "dayofweek": row.get("dayofweek"),
    }
    
    sql = """
    INSERT INTO sensor_hourly 
    (ts, temp, humidity, wind_speed, pm25, co2_ppm, latency_ms, latency_ok, uptime_ok,
    recovery_sec, recovery_ok, energy_kwh, cost_idr, eui_kwh_m2, pmv, ppd, pmv_label, dayofweek)

    VALUES
    (%(ts)s, %(temp)s, %(humidity)s, %(wind_speed)s, %(pm25)s, %(co2_ppm)s, 
     %(latency_ms)s, %(latency_ok)s, %(uptime_ok)s,
     %(recovery_sec)s, %(recovery_ok)s,
     %(energy_kwh)s, %(cost_idr)s, %(eui_kwh_m2)s, %(pmv)s, %(ppd)s, %(pmv_label)s, %(dayofweek)s)
    ON CONFLICT (ts) DO NOTHING
    """

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, transformed_row)