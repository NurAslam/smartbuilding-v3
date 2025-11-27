# Forecast API Documentation

## Overview

Forecasting module yang mengambil data historical dari database (`sensor_hourly`) dan menggunakan LSTM/RNN models untuk prediksi. **Data automatically updated setiap ada data baru di database** - tidak perlu manual retraining.

## Features

✅ **Automatic Data Source**: Data diambil langsung dari `sensor_hourly` (monitoring real-time)  
✅ **Auto-Update**: Model otomatis dilatih ulang setiap ada data baru (di-detect via data hash)  
✅ **Model Caching**: Model disimpan ke disk (`/tmp/bima_forecast_models/`) untuk inference lebih cepat  
✅ **CPU Optimized**: LSTM dan RNN dioptimasi untuk CPU deployment (small layers: 32 units)  
✅ **Multiple Metrics**: Support semua metrics dari database (temp, humidity, wind_speed, pm25, co2)  
✅ **Flexible Granularity**: Daily (24 jam), Weekly (7 hari), Monthly (30 hari)

---

## Endpoints

### 1. Daily Forecast (24 jam ke depan)

**GET** `/realtime/forecast/daily`

Forecast 24 jam ke depan menggunakan hourly historical data.

#### Query Parameters

| Parameter      | Type    | Default | Description                                             |
| -------------- | ------- | ------- | ------------------------------------------------------- |
| `model_type`   | string  | `lstm`  | Model: `lstm` atau `rnn`                                |
| `metric`       | string  | `temp`  | Metric: `temp`, `humidity`, `wind_speed`, `pm25`, `co2` |
| `hours`        | integer | `72`    | Historical hours untuk training (min 24, max 240)       |
| `ref_datetime` | string  | current | Reference datetime ISO format (YYYY-MM-DDTHH:MM:SS)     |

#### Examples

```bash
# Default: forecast temp 24 jam dengan LSTM, training 72 jam terakhir
curl "http://localhost:8000/realtime/forecast/daily"

# Forecast humidity dengan RNN, training 120 jam
curl "http://localhost:8000/realtime/forecast/daily?metric=humidity&model_type=rnn&hours=120"

# Forecast untuk reference datetime spesifik
curl "http://localhost:8000/realtime/forecast/daily?ref_datetime=2025-11-27T15:30:00"
```

#### Response Example

```json
{
  "granularity": "daily",
  "metric": "temp",
  "forecast_hours": 24,
  "forecast": [
    23.5, 23.8, 24.1, 24.3, 24.5, 24.2, 23.9, 23.6, 23.4, 23.2, 22.8, 22.5,
    22.3, 22.1, 22.0, 22.5, 23.0, 23.5, 24.0, 24.3, 24.5, 24.2, 23.8, 23.5
  ],
  "model_used": "LSTM",
  "ref_datetime": "2025-11-27T15:30:00+07:00",
  "forecast_start": "2025-11-27T15:30:00+07:00",
  "forecast_end": "2025-11-28T15:30:00+07:00",
  "training_datapoints": 72
}
```

---

### 2. Weekly Forecast (7 hari ke depan)

**GET** `/realtime/forecast/weekly`

Forecast 7 hari ke depan menggunakan daily aggregated data.

#### Query Parameters

| Parameter    | Type    | Default | Description                                             |
| ------------ | ------- | ------- | ------------------------------------------------------- |
| `model_type` | string  | `lstm`  | Model: `lstm` atau `rnn`                                |
| `metric`     | string  | `temp`  | Metric: `temp`, `humidity`, `wind_speed`, `pm25`, `co2` |
| `days`       | integer | `30`    | Historical days untuk training (min 14, max 90)         |
| `ref_date`   | string  | today   | Reference date ISO format (YYYY-MM-DD)                  |

#### Examples

```bash
# Default: forecast temp 7 hari dengan LSTM, training 30 hari terakhir
curl "http://localhost:8000/realtime/forecast/weekly"

# Forecast humidity untuk minggu tertentu
curl "http://localhost:8000/realtime/forecast/weekly?metric=humidity&ref_date=2025-11-20"

# Forecast pm25 dengan RNN, training 60 hari
curl "http://localhost:8000/realtime/forecast/weekly?metric=pm25&model_type=rnn&days=60"
```

#### Response Example

```json
{
  "granularity": "weekly",
  "metric": "temp",
  "forecast_days": 7,
  "forecast": [25.3, 24.8, 23.9, 22.5, 21.8, 22.3, 23.5],
  "model_used": "LSTM",
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

---

### 3. Monthly Forecast (30 hari ke depan)

**GET** `/realtime/forecast/monthly`

Forecast 30 hari ke depan menggunakan daily aggregated data.

#### Query Parameters

| Parameter    | Type    | Default | Description                                             |
| ------------ | ------- | ------- | ------------------------------------------------------- |
| `model_type` | string  | `lstm`  | Model: `lstm` atau `rnn`                                |
| `metric`     | string  | `temp`  | Metric: `temp`, `humidity`, `wind_speed`, `pm25`, `co2` |
| `days`       | integer | `90`    | Historical days untuk training (min 30, max 365)        |
| `ref_date`   | string  | today   | Reference date ISO format (YYYY-MM-DD)                  |

#### Examples

```bash
# Default: forecast temp 30 hari dengan LSTM, training 90 hari terakhir
curl "http://localhost:8000/realtime/forecast/monthly"

# Forecast co2 dengan RNN, training 180 hari
curl "http://localhost:8000/realtime/forecast/monthly?metric=co2&model_type=rnn&days=180"

# Forecast untuk bulan spesifik
curl "http://localhost:8000/realtime/forecast/monthly?ref_date=2025-11-01"
```

#### Response Example

```json
{
  "granularity": "monthly",
  "metric": "temp",
  "forecast_days": 30,
  "forecast": [
    25.3, 24.8, 23.9, 22.5, 21.8, 22.3, 23.5, 24.1, 24.8, 25.2, 25.5, 25.3,
    24.9, 24.2, 23.5, 22.8, 22.1, 21.9, 22.5, 23.2, 24.0, 24.8, 25.3, 25.6,
    25.4, 24.8, 24.1, 23.3, 22.5, 21.8
  ],
  "model_used": "LSTM",
  "ref_date": "2025-11-27",
  "forecast_start": "2025-11-27",
  "forecast_end": "2025-12-27",
  "training_datapoints": 90
}
```

---

## How It Works

### Data Flow

```
Database (sensor_hourly)
    ↓
_series_bucket() - Query historical data (hourly/daily aggregation)
    ↓
forecast_daily/weekly/monthly() - Process data with LSTM/RNN
    ↓
Model Cache Check - Load cached model if data unchanged
    ↓
Train or Load Model - Auto-retrain if data hash changed
    ↓
Inference - Generate forecast for N hours/days
    ↓
API Response
```

### Automatic Update Mechanism

1. **Data Hash Tracking**: Setiap request, sistem hitung MD5 hash dari historical data
2. **Cache Check**: Jika hash cocok dengan cached model → load dari cache (cepat)
3. **Auto-Retrain**: Jika hash berbeda (ada data baru) → train model baru (lambat tapi akurat)
4. **Persistence**: Model disimpan ke `/tmp/bima_forecast_models/` untuk reuse

### Model Configuration

**LSTM Model:**

- Layers: 1 LSTM (32 units) + Dropout(0.1) + Dense(16) + Dense(1)
- Optimizer: Adam (lr=0.001)
- Loss: MSE
- Epochs: Daily=10, Weekly=15, Monthly=20

**RNN Model:**

- Layers: 1 SimpleRNN (32 units) + Dropout(0.1) + Dense(16) + Dense(1)
- Optimizer: Adam (lr=0.001)
- Loss: MSE
- Epochs: Daily=10, Weekly=15, Monthly=20

Both models use **MinMaxScaler normalization** untuk stability.

---

## Metrics Reference

| Metric       | Unit  | Description                                         |
| ------------ | ----- | --------------------------------------------------- |
| `temp`       | °C    | Temperature (dari `sensor_hourly.temp`)             |
| `humidity`   | %     | Relative humidity (dari `sensor_hourly.humidity`)   |
| `wind_speed` | m/s   | Wind speed (dari `sensor_hourly.wind_speed`)        |
| `pm25`       | µg/m³ | Fine particulate matter (dari `sensor_hourly.pm25`) |
| `co2`        | ppm   | Carbon dioxide (dari `sensor_hourly.co2`)           |

---

## Cache Directory

Models dan metadata disimpan di: `/tmp/bima_forecast_models/`

### File Structure

```
/tmp/bima_forecast_models/
├── daily_temp_lstm_model.h5          # Model file
├── daily_temp_lstm_scaler.pkl        # Scaler untuk denormalization
├── weekly_temp_lstm_model.h5
├── weekly_temp_lstm_scaler.pkl
├── monthly_temp_lstm_model.h5
├── monthly_temp_lstm_scaler.pkl
├── daily_humidity_rnn_model.h5
├── daily_humidity_rnn_scaler.pkl
├── ...
└── metadata.json                     # Cache metadata & data hashes
```

### Metadata Structure

```json
{
  "daily_temp_lstm": {
    "data_hash": "abc123def456...",
    "data_length": 72,
    "trained_at": "2025-11-27T15:30:00",
    "model_type": "lstm",
    "granularity": "daily",
    "metric": "temp"
  },
  "weekly_humidity_rnn": {
    "data_hash": "xyz789...",
    "data_length": 30,
    "trained_at": "2025-11-27T14:00:00",
    "model_type": "rnn",
    "granularity": "weekly",
    "metric": "humidity"
  }
}
```

---

## Error Handling

### Common Errors

**400 Bad Request - Data tidak cukup**

```json
{
  "detail": "Data tidak cukup (butuh min 7 points, dapat 3)"
}
```

**Solution**: Tingkatkan parameter `hours`/`days` atau tunggu lebih banyak data tersimpan di database.

**400 Bad Request - Invalid datetime format**

```json
{
  "detail": "ref_datetime harus ISO format (YYYY-MM-DDTHH:MM:SS)"
}
```

**Solution**: Gunakan format ISO yang benar.

**404 Not Found - Tidak ada data**

```json
{
  "detail": "Tidak ada data untuk forecast (temp)."
}
```

**Solution**: Pastikan database punya data untuk metric dan periode yang diminta.

**500 Internal Server Error**

```json
{
  "detail": "Forecast error: [error message]"
}
```

**Solution**: Check server logs untuk detail error.

---

## Performance Notes

- **Daily forecast**: ~1-2 detik (training + inference)
- **Weekly forecast**: ~2-3 detik (training + inference)
- **Monthly forecast**: ~3-5 detik (training + inference)
- **Cached load** (model tidak berubah): ~100-200ms (very fast)

---

## Integration Examples

### Python Requests

```python
import requests
import json

BASE_URL = "http://localhost:8000/realtime/forecast"

# Daily forecast
response = requests.get(
    f"{BASE_URL}/daily",
    params={
        "model_type": "lstm",
        "metric": "temp",
        "hours": 72
    }
)
forecast_data = response.json()
print(json.dumps(forecast_data, indent=2))

# Weekly forecast
response = requests.get(
    f"{BASE_URL}/weekly",
    params={
        "model_type": "rnn",
        "metric": "humidity",
        "days": 30
    }
)
print(response.json())
```

### JavaScript Fetch

```javascript
async function getWeeklyForecast() {
  const response = await fetch(
    "/realtime/forecast/weekly?model_type=lstm&metric=temp&days=30"
  );
  const data = await response.json();
  console.log(data);

  // Plot forecast
  const temps = data.forecast;
  const labels = data.forecast_days_labels;
  // ... plot dengan chart library
}
```

---

## Dashboard Integration

Untuk dashboard real-time, gunakan endpoints ini:

```html
<!-- Temperature Forecast Card -->
<div class="forecast-card">
  <h3>Temperature Forecast (24h)</h3>
  <canvas id="temp-forecast"></canvas>
  <script>
    fetch("/realtime/forecast/daily?metric=temp")
      .then((r) => r.json())
      .then((data) => plotChart(data.forecast, 24));
  </script>
</div>

<!-- Weekly Humidity -->
<div class="forecast-card">
  <h3>Weekly Humidity Forecast</h3>
  <canvas id="humidity-weekly"></canvas>
  <script>
    fetch("/realtime/forecast/weekly?metric=humidity")
      .then((r) => r.json())
      .then((data) => plotChart(data.forecast, data.forecast_days_labels));
  </script>
</div>
```

---

## Troubleshooting

### Model not loading from cache

Check `/tmp/bima_forecast_models/metadata.json` untuk melihat cache status:

```bash
cat /tmp/bima_forecast_models/metadata.json
```

### Clear cache (force retrain)

```bash
rm -rf /tmp/bima_forecast_models/
```

### Check data availability

```bash
# Query sensor_hourly untuk verify data exists
psql -h localhost -U postgres -d smartbuilding -c \
  "SELECT COUNT(*), MIN(ts), MAX(ts) FROM sensor_hourly WHERE ts > NOW() - INTERVAL '90 days';"
```

---

## Future Enhancements

- [ ] Confidence intervals (±std dev)
- [ ] Ensemble forecasting (multiple models)
- [ ] Custom metric combinations
- [ ] Forecast accuracy tracking
- [ ] Automated alert thresholds
- [ ] Model performance visualization
