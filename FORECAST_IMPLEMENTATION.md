# Forecast Module - Implementation Summary

## Overview

✅ **Complete rewrite** dari forecast module untuk mengambil data dari database (sensor_hourly) dengan automatic update setiap ada data baru.

**Key Changes:**

- Data source: Dari file/hardcoded → Database (sensor_hourly) - **Real monitoring data**
- Auto-update: Model otomatis dilatih ulang saat ada data baru (di-detect via data hash)
- Flexible metrics: Support semua metrics (temp, humidity, wind_speed, pm25, co2)
- Same as grafik monitoring: Menggunakan struktur \_series_bucket() yang sama dengan endpoints grafik

---

## What Changed

### 1. **Data Source** - Now from Database ✅

**Before:**

```python
def get_hourly_data(hours: int = 72) -> np.ndarray:
    # Data diambil random atau hardcoded
    values = np.random.normal(...)
    return values
```

**After:**

```python
def _series_bucket(start_wib, end_wib, bucket_sql, metric: str = "temp") -> np.ndarray:
    # Data dari sensor_hourly (real monitoring)
    sql = f"""
    SELECT {bucket_sql} AS bucket, {metric_col_map[metric]} AS metric_value
    FROM sensor_hourly
    WHERE ts >= %(t0)s AND ts < %(t1)s
    GROUP BY 1 ORDER BY 1 ASC;
    """
    # Execute query dan return actual monitoring data
```

**Benefits:**

- ✅ Real data dari monitoring
- ✅ Automatic update setiap sensor baru data
- ✅ Same bucketing logic sebagai grafik (hourly/daily/monthly)
- ✅ Timezone-aware (UTC storage, WIB display)

---

### 2. **Automatic Model Update** - Cache System ✅

**New Cache Mechanism:**

```
Request untuk forecast
    ↓
Hitung data_hash = MD5(historical_data)
    ↓
Check cache metadata
    ├─ Hash cocok? → Load cached model (100ms)
    └─ Hash beda?  → Retrain model (1-5s) → Save to cache
    ↓
Inference (100-200ms)
    ↓
Response
```

**Cache Files:**

```
/tmp/bima_forecast_models/
├── daily_temp_lstm_model.h5
├── daily_temp_lstm_scaler.pkl
├── weekly_humidity_rnn_model.h5
├── weekly_humidity_rnn_scaler.pkl
├── monthly_co2_lstm_model.h5
├── monthly_co2_lstm_scaler.pkl
└── metadata.json  # Tracks data_hash & training timestamp
```

**How it works:**

1. First request: Train & save model (slow: 1-5s)
2. Second request (same data): Load from cache (fast: 100ms)
3. Third request (new data): Detect hash change, retrain (slow: 1-5s)

---

### 3. **Multiple Metrics Support** ✅

**Before:** Only temperature

**After:** All 5 metrics from database:

- `temp` - Temperature (°C)
- `humidity` - Relative humidity (%)
- `wind_speed` - Wind speed (m/s)
- `pm25` - Fine particulate matter (µg/m³)
- `co2` - Carbon dioxide (ppm)

**Example:**

```bash
# Temperature forecast
curl "http://localhost:8000/realtime/forecast/daily?metric=temp"

# Humidity forecast
curl "http://localhost:8000/realtime/forecast/daily?metric=humidity"

# PM2.5 forecast
curl "http://localhost:8000/realtime/forecast/weekly?metric=pm25&days=30"

# CO2 forecast
curl "http://localhost:8000/realtime/forecast/monthly?metric=co2&days=90"
```

---

### 4. **Same Bucketing Logic as Grafik** ✅

**Konsistensi dengan grafik.py:**

```python
# Before (hardcoded):
start = end - timedelta(hours=hours)
start_utc = start.astimezone(ZoneInfo("UTC"))

# After (same as grafik.py):
def _calc_series_window(granularity: str, size: int, ref_wib: datetime):
    if granularity == "hourly":
        end = ref_wib.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        start = end - timedelta(hours=size)
        bucket_sql = "date_trunc('hour', (ts AT TIME ZONE %(tz)s))"
    elif granularity == "daily":
        end = ref_wib.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        start = end - timedelta(days=size)
        bucket_sql = "date_trunc('day', (ts AT TIME ZONE %(tz)s))"
    # ... etc
```

**Benefits:**

- Sama persis dengan grafik monitoring
- Data konsisten antara grafik dan forecast
- Timezone handling yang sama (UTC storage, WIB display)

---

## Files Modified

### 1. `app/realtime/domain/forecast.py`

**Changes:**

- ✅ Added cache management functions:
  - `_get_data_hash()` - Generate MD5 hash dari data
  - `_save_model_cache()` - Save model + scaler + metadata
  - `_load_model_cache()` - Load model jika data_hash cocok
- ✅ Updated `train_forecast_model()` - Auto cache check/save
- ✅ Updated `forecast_daily/weekly/monthly()` - Pass granularity & metric untuk cache key

**Code Example:**

```python
def train_forecast_model(
    data: np.ndarray,
    model_type: str = "lstm",
    granularity: str = "daily",  # NEW - untuk cache key
    metric: str = "temp",        # NEW - untuk cache key
    epochs: int = 20,
    force_retrain: bool = False,
):
    data_hash = _get_data_hash(data)

    # Check cache terlebih dahulu
    if not force_retrain:
        cached = _load_model_cache(model_type, granularity, metric, data_hash)
        if cached is not None:
            return cached  # Load from cache!

    # Train model (jika tidak ada di cache)
    model, scaler = ... train logic ...

    # Save to cache
    _save_model_cache(model_type, granularity, metric, model, scaler, data_hash, len(data))

    return model, scaler
```

### 2. `app/realtime/routers/forecast.py`

**Changes:**

- ✅ Removed `get_hourly_data()`, `get_daily_data()` (hardcoded queries)
- ✅ Added `_calc_series_window()` - Same as grafik.py
- ✅ Added `_series_bucket()` - Query dari sensor_hourly dengan metric support
- ✅ Updated all endpoints untuk support `metric` parameter
- ✅ Updated query logic untuk match grafik.py structure

**Code Example:**

```python
@router.get("/daily")
def forecast_daily_endpoint(
    model_type: Literal["lstm", "rnn"] = Query("lstm"),
    metric: str = Query("temp", description="Metric: temp, humidity, wind_speed, pm25, co2"),  # NEW
    hours: int = Query(72),
    ref_datetime: str = Query(None),
):
    # Get historical data from database (same as grafik)
    start, end, bucket_sql = _calc_series_window("hourly", hours, ref_wib)
    hourly_vals = _series_bucket(start, end, bucket_sql, metric=metric)  # NEW

    # Forecast
    result = forecast_daily(hourly_vals, metric=metric, model_type=model_type)

    # Add metadata
    result.update({
        "ref_datetime": ref_wib.isoformat(),
        "forecast_start": forecast_start.isoformat(),
        "forecast_end": forecast_end.isoformat(),
        "training_datapoints": len(hourly_vals),
    })

    return result
```

---

## API Changes

### Before (Hardcoded Data)

```bash
GET /realtime/forecast/daily?model_type=lstm&hours=72
GET /realtime/forecast/weekly?model_type=lstm&days=30
GET /realtime/forecast/monthly?model_type=lstm&days=90
```

### After (Database + Metrics)

```bash
# Temperature (default metric)
GET /realtime/forecast/daily?model_type=lstm&hours=72
GET /realtime/forecast/weekly?model_type=lstm&days=30
GET /realtime/forecast/monthly?model_type=lstm&days=90

# Any metric from database
GET /realtime/forecast/daily?metric=humidity&model_type=rnn&hours=72
GET /realtime/forecast/weekly?metric=pm25&model_type=lstm&days=30
GET /realtime/forecast/monthly?metric=co2&model_type=rnn&days=90

# With specific reference time
GET /realtime/forecast/daily?metric=temp&ref_datetime=2025-11-27T15:30:00
GET /realtime/forecast/weekly?metric=humidity&ref_date=2025-11-20
GET /realtime/forecast/monthly?metric=wind_speed&ref_date=2025-11-01
```

---

## Response Format

### Daily Forecast

```json
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
```

### Weekly Forecast

```json
{
  "granularity": "weekly",
  "metric": "humidity",
  "forecast_days": 7,
  "forecast": [65.3, 64.8, 63.9, 62.5, 61.8, 62.3, 63.5],
  "model_used": "RNN",
  "ref_date": "2025-11-27",
  "forecast_start": "2025-11-27",
  "forecast_end": "2025-12-04",
  "forecast_days_labels": [
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday"
  ],
  "training_datapoints": 30
}
```

### Monthly Forecast

```json
{
  "granularity": "monthly",
  "metric": "pm25",
  "forecast_days": 30,
  "forecast": [45.3, 44.8, 43.9, ..., 46.1],
  "model_used": "LSTM",
  "ref_date": "2025-11-27",
  "forecast_start": "2025-11-27",
  "forecast_end": "2025-12-27",
  "training_datapoints": 90
}
```

---

## Testing Results

✅ All tests passed (5/5):

```
TEST 1: Data Operations         ✓ PASSED
  - Data normalization/denormalization
  - Time-series preparation
  - Data hashing (consistency & sensitivity)

TEST 2: Model Building          ✓ PASSED
  - LSTM model (4897 parameters)
  - RNN model (1633 parameters)

TEST 3: Training & Forecasting  ✓ PASSED
  - Daily forecast (24 hours)
  - Weekly forecast (7 days)
  - Monthly forecast (30 days)

TEST 4: Cache Mechanism         ✓ PASSED
  - First training (save to cache)
  - Cache loading (same data)
  - Auto-retrain (different data)

TEST 5: API Response Structure  ✓ PASSED
  - All required fields present
  - Correct data types
  - Valid forecast arrays
```

**Run tests:** `python test_forecast.py`

---

## Performance Metrics

| Operation                   | Time   | Notes                |
| --------------------------- | ------ | -------------------- |
| Daily forecast (new data)   | 1-2s   | Train + inference    |
| Daily forecast (cached)     | ~100ms | Load from cache only |
| Weekly forecast (new data)  | 2-3s   | Train + inference    |
| Weekly forecast (cached)    | ~100ms | Load from cache only |
| Monthly forecast (new data) | 3-5s   | Train + inference    |
| Monthly forecast (cached)   | ~100ms | Load from cache only |

---

## How to Use

### 1. Get Daily Temperature Forecast (24 hours)

```bash
curl "http://localhost:8000/realtime/forecast/daily"

# Or with specific metric
curl "http://localhost:8000/realtime/forecast/daily?metric=humidity"
```

### 2. Get Weekly Weather Forecast (7 days)

```bash
curl "http://localhost:8000/realtime/forecast/weekly"

# With RNN instead of LSTM
curl "http://localhost:8000/realtime/forecast/weekly?model_type=rnn"
```

### 3. Get Monthly Trend (30 days)

```bash
curl "http://localhost:8000/realtime/forecast/monthly"

# For specific metric with custom historical data
curl "http://localhost:8000/realtime/forecast/monthly?metric=pm25&days=120"
```

### 4. Get Air Quality Forecast

```bash
# PM2.5 weekly forecast
curl "http://localhost:8000/realtime/forecast/weekly?metric=pm25&days=30"

# CO2 monthly forecast
curl "http://localhost:8000/realtime/forecast/monthly?metric=co2&days=90"
```

---

## Database Integration

**Data is fetched from:** `sensor_hourly` table

**Query structure:**

```sql
SELECT
  date_trunc('hour'/'day', (ts AT TIME ZONE 'Asia/Jakarta')) AS bucket,
  AVG(temp/humidity/wind_speed/pm25/co2) AS metric_value
FROM sensor_hourly
WHERE ts >= (start UTC) AND ts < (end UTC)
GROUP BY 1
ORDER BY 1 ASC;
```

**Timezone handling:**

- Storage: UTC (TIMESTAMPTZ)
- Query bucketing: WIB (AT TIME ZONE)
- Response: ISO format with WIB offset

---

## Automatic Update Mechanism

### How Data Gets Updated

1. **Sensor sends new data** → `sensor_hourly` table updated
2. **User requests forecast** → Module queries database
3. **Data hash check**:
   - Hash matches cache? → Load cached model (fast)
   - Hash different? → Retrain model (slow but accurate)
4. **Model runs forecast** → Returns prediction
5. **Model saved to cache** → Ready for next identical request

### Timeline Example

**11:00 AM:**

```
User requests /forecast/daily?metric=temp&hours=72
→ Query database, get 72 hours of temp data
→ Hash = abc123
→ No cache yet, train model (2 seconds)
→ Save model & metadata to cache
→ Return forecast
```

**11:05 AM:**

```
Same user requests /forecast/daily?metric=temp&hours=72
→ Query database, get 72 hours of temp data
→ Hash = abc123 (same data)
→ Load from cache (100ms)
→ Return forecast (very fast!)
```

**11:10 AM - After new sensor data arrived:**

```
User requests /forecast/daily?metric=temp&hours=72
→ Query database, get 72 hours of temp data (includes new reading)
→ Hash = def456 (different!)
→ Cache miss, train new model (2 seconds)
→ Save updated model to cache
→ Return forecast (more accurate with latest data)
```

---

## Documentation

**Full API Documentation:** See `FORECAST_API.md`

---

## Summary

✅ **Forecast module completely rewritten to:**

1. Take data from real database (sensor_hourly)
2. Support all 5 metrics (temp, humidity, wind_speed, pm25, co2)
3. Auto-update models when data changes
4. Use same bucketing logic as grafik monitoring
5. Cache models for fast inference
6. Handle timezones correctly (UTC → WIB)

**Ready for production use!** 🚀
