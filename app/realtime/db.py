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
        uptime_ok BOOLEAN NOT NULL DEFAULT 0,
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
    sql = """
    INSERT INTO sensor_hourly 
    (ts, temp, humidity, wind_speed, pm25, co2, latency_sec, uptime_pct,
    energy_kwh, cost_idr, eui_kwh_m2, pmv, ppd, pmv_label, dayofweek)

    VALUES
            (%(ts)s, %(temp)s, %(humidity)s, %(wind_speed)s, %(pm25)s, %(co2)s, %(latency_sec)s, %(uptime_pct)s,
            %(energy_kwh)s, %(cost_idr)s, %(eui_kwh_m2)s, %(pmv)s, %(ppd)s, %(pmv_label)s, %(dayofweek)s)
    ON CONFLICT (ts) DO NOTHING
    """

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, row)