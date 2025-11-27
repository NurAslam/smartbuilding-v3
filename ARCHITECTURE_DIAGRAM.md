# Implementation Architecture Diagram

## Overall System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Application                         │
│                      (app/main.py)                              │
└─────────────────────────────────────────────────────────────────┘
                              ▼
        ┌─────────────────────────────────────────┐
        │   Router Registration                   │
        ├─────────────────────────────────────────┤
        │  Simulation:                            │
        │    - /simulation/predict                │
        │    - /simulation/analyze                │
        │                                         │
        │  Realtime - Environmental Forecast:    │
        │    - /realtime/forecast/daily          │
        │    - /realtime/forecast/weekly         │
        │    - /realtime/forecast/monthly        │
        │                                         │
        │  Realtime - ENERGY & COMFORT (NEW):   │
        │    - /realtime/forecast-energy/*       │
        │    - /realtime/forecast-comfort/*      │
        │                                         │
        │  Realtime - Monitoring:                │
        │    - /realtime/monitoring/series       │
        └─────────────────────────────────────────┘
```

---

## Energy & Comfort Forecast Flow

### 1. Request Flow (Daily Example)

```
┌─────────────────────────────────────────────────────────────────┐
│ User Request                                                    │
│ GET /realtime/forecast-energy/daily?hours=72                  │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ forecast_energy_daily_endpoint()                                │
│ - Parse query parameters (model_type, hours, ref_datetime)     │
│ - Validate input (hours: 24-240)                               │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ _calc_series_window("hourly", 72, ref_wib)                     │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Granularity: hourly                                         │ │
│ │ End: ref_wib.replace(min, sec) + 1 hour                    │ │
│ │ Start: end - 72 hours                                       │ │
│ │ SQL: date_trunc('hour', ts AT TIME ZONE 'Asia/Jakarta')   │ │
│ └─────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ _series_bucket(start, end, bucket_sql, metric="energy_kwh")    │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Database Query:                                             │ │
│ │ SELECT avg(energy_kwh) AS metric_value                      │ │
│ │ FROM sensor_hourly                                          │ │
│ │ WHERE ts >= start_utc AND ts < end_utc                      │ │
│ │ GROUP BY date_trunc('hour', ts AT TIME ZONE 'Asia/Jakarta')│ │
│ │ ORDER BY 1 ASC                                              │ │
│ │                                                             │ │
│ │ Result: [0.732, 0.734, 0.725, ... ] (72 values)            │ │
│ └─────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ Validate Data                                                   │
│ if len(hourly_vals) < 7: raise HTTPException(400)              │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ forecast_daily(hourly_vals, metric="energy_kwh", model="lstm")  │
│ (from app/realtime/domain/forecast.py)                          │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 1. Calculate data hash                                      │ │
│ │ 2. Check cache for existing model                           │ │
│ │                                                             │ │
│ │ CACHE HIT (model exists & hash matches):                   │ │
│ │ ├─ Load model from /tmp/bima_forecast_models/              │ │
│ │ ├─ Load scaler from pickle file                            │ │
│ │ └─ Time: ~100ms                                             │ │
│ │                                                             │ │
│ │ CACHE MISS (first time or data changed):                   │ │
│ │ ├─ Normalize data with MinMaxScaler                        │ │
│ │ ├─ Create sequences (LOOK_BACK=7)                          │ │
│ │ ├─ Build LSTM model:                                        │ │
│ │ │   - Input: (batch, 7, 1)                                 │ │
│ │ │   - LSTM(32) + Dropout(0.1) + Dense(1)                   │ │
│ │ │   - Loss: mse, Optimizer: Adam                           │ │
│ │ ├─ Train on 72 data points                                 │ │
│ │ ├─ Save model to disk (H5 format)                          │ │
│ │ ├─ Save scaler to disk (pickle)                            │ │
│ │ ├─ Update metadata.json with hash                          │ │
│ │ └─ Time: 2-5 seconds                                        │ │
│ │                                                             │ │
│ │ 3. Recursive prediction (forecast_ahead):                   │ │
│ │ ├─ Last 7 normalized values                                │ │
│ │ ├─ Predict 1 step ahead                                    │ │
│ │ ├─ Append to sequence                                      │ │
│ │ ├─ Remove oldest, repeat 24 times                          │ │
│ │ └─ Result: 24 forecast values                              │ │
│ │                                                             │ │
│ │ 4. Denormalize using scaler                                │ │
│ │    Return: {"metric": "energy_kwh", "forecast": [...]}     │ │
│ └─────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ Generate Timestamps                                             │
│ _generate_hourly_timestamps(forecast_start, 24)                │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ for i in range(24):                                         │ │
│ │   timestamp = forecast_start + timedelta(hours=i)           │ │
│ │   timestamp.isoformat()  # "2025-11-27T22:00:00+07:00"    │ │
│ │                                                             │ │
│ │ Result: List of 24 ISO datetime strings                     │ │
│ └─────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ Create Response                                                 │
│ {                                                               │
│   "metric": "energy_kwh",                                       │
│   "granularity": "daily",                                       │
│   "forecast": [0.732, 0.734, ...],  (24 values)                │
│   "forecast_with_timestamps": [                                 │
│     {"timestamp": "2025-11-27T22:00:00+07:00", "value": 0.732}, │
│     ...                                                         │
│   ],                                                            │
│   "model_used": "LSTM",                                         │
│   "ref_datetime": "2025-11-27T22:00:00+07:00",                 │
│   "forecast_start": "2025-11-27T22:00:00+07:00",               │
│   "forecast_end": "2025-11-28T22:00:00+07:00",                 │
│   "training_datapoints": 72                                     │
│ }                                                               │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ Return JSON Response (HTTP 200)                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     PostgreSQL Database                          │
│                    (sensor_hourly table)                         │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Columns:                                                   │  │
│  │ - ts (timestamp with timezone)                             │  │
│  │ - temp, humidity, wind_speed, pm25, co2                    │  │
│  │ - energy_kwh          ← Energy Forecast uses this         │  │
│  │ - pmv                 ← Comfort (PPV) Forecast uses this  │  │
│  │ - ppd                 ← Comfort (PPD) Forecast uses this  │  │
│  │ - other columns...                                         │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────┬───────────────────────────────────────────────────┘
               │
               │ (SQL Query)
               ▼
┌──────────────────────────────────────────────────────────────────┐
│         Forecast Routers (forecast_energy_comfort.py)            │
│                                                                  │
│  ┌─────────────────────────┬──────────────────────────────────┐  │
│  │ Energy Router           │ Comfort Router                   │  │
│  ├─────────────────────────┼──────────────────────────────────┤  │
│  │ /daily                  │ /daily                           │  │
│  │ /weekly                 │ /weekly                          │  │
│  │ /monthly                │ /monthly                         │  │
│  │                         │                                  │  │
│  │ Metrics: energy_kwh     │ Metrics: ppv, ppd                │  │
│  └─────────────────────────┴──────────────────────────────────┘  │
└──────────────┬───────────────────────────────────────────────────┘
               │
               │ (Uses)
               ▼
┌──────────────────────────────────────────────────────────────────┐
│    Domain Forecast Module (app/realtime/domain/forecast.py)      │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ forecast_daily()                                         │   │
│  │ forecast_weekly()                                        │   │
│  │ forecast_monthly()                                       │   │
│  │                                                          │   │
│  │ - Handle LSTM/RNN model training                         │   │
│  │ - Normalize with MinMaxScaler                            │   │
│  │ - Cache models to disk (/tmp/bima_forecast_models/)     │   │
│  │ - Recursive prediction                                   │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────┬───────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────┐
│               Model Cache (Disk)                                 │
│        /tmp/bima_forecast_models/                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ daily_energy_kwh_lstm_model.h5       (HDF5 model)       │   │
│  │ daily_energy_kwh_lstm_scaler.pkl     (Pickle scaler)    │   │
│  │ daily_ppv_lstm_model.h5                                 │   │
│  │ daily_ppd_rnn_model.h5                                  │   │
│  │ weekly_energy_kwh_lstm_model.h5                          │   │
│  │ monthly_energy_kwh_rnn_model.h5                          │   │
│  │ ... (more models)                                        │   │
│  │ metadata.json      (Hash tracking for cache hits/miss)   │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────┬───────────────────────────────────────────────────┘
               │
               │ (Returns)
               ▼
┌──────────────────────────────────────────────────────────────────┐
│                    API Response                                  │
│           (JSON with forecast_with_timestamps)                   │
└──────────────────────────────────────────────────────────────────┘
               │
               │ (HTTP 200 OK)
               ▼
        ┌──────────────────┐
        │  Frontend/Client │
        │  (Display Chart) │
        └──────────────────┘
```

---

## File Structure

```
app/
├── main.py                                  ← Registers routers
│   ├── from forecast_energy_comfort import router, energy_router
│   └── app.include_router(comfort_router, energy_router)
│
├── realtime/
│   ├── db.py                               ← Database connection
│   │   └── insert_row(), get_conn()
│   │
│   ├── domain/
│   │   └── forecast.py                     ← Model training
│   │       ├── forecast_daily()
│   │       ├── forecast_weekly()
│   │       └── forecast_monthly()
│   │
│   └── routers/
│       ├── forecast.py                     ← Environmental forecast (existing)
│       │   ├── /forecast/daily
│       │   ├── /forecast/weekly
│       │   └── /forecast/monthly
│       │
│       └── forecast_energy_comfort.py      ← ENERGY & COMFORT (NEW)
│           ├── router (comfort endpoints)
│           │   ├── /forecast-comfort/daily
│           │   ├── /forecast-comfort/weekly
│           │   └── /forecast-comfort/monthly
│           │
│           └── energy_router
│               ├── /forecast-energy/daily
│               ├── /forecast-energy/weekly
│               └── /forecast-energy/monthly
│
└── simulation/
    └── routers/
        ├── predict.py                      ← For prediction with trained models
        └── models.py
```

---

## Key Implementation Features

### 1. Time Window Calculation

```
Daily:    ├─ 72 hours back ────────┤ now+1h │
          └─ Hourly aggregation    │

Weekly:   ├─ 90 days back ─────────────────────┤ tomorrow 00:00 │
          └─ Daily aggregation                 │

Monthly:  ├─ 90-365 days back ─────────────────────────────────┤
          └─ Daily aggregation                                   │
```

### 2. Model Types

```
LSTM (32 units)              RNN (32 units)
├─ Better for long patterns  ├─ Simpler
├─ Default                   ├─ Lighter weight
└─ Used by default           └─ Available via model_type=rnn
```

### 3. Prediction Process

```
Input Data (7 points)
        ▼
Normalize (0-1 range)
        ▼
LSTM/RNN Model
├─ Input shape: (batch, 7, 1)
├─ Lookback: 7 timesteps
└─ Output: 1 value
        ▼
Recursive Loop (24/7/30 iterations)
├─ Predict 1 step
├─ Add to sequence
├─ Remove oldest
└─ Repeat
        ▼
Denormalize to original scale
        ▼
Return 24/7/30 forecast values
```

---

## ✅ Complete Implementation

**All components working together to provide:**

- 6 endpoints for energy and comfort forecasting
- Automatic model training and caching
- Hourly/daily/weekly/monthly granularities
- Timestamp arrays for frontend integration
- Same architecture as environmental forecasts
