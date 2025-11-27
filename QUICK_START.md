# 🚀 Quick Start - Forecast Module

## 1. Start Server

```bash
cd "/Users/user/Documents/03 KERJA/PT Multimedia Solusi Prima/2025/NOVEMBER/BIMA"

# Activate virtual environment
source bimavenv/bin/activate

# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Output:**

```
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## 2. Test Forecast Endpoints

### Test 1: Daily Temperature Forecast (Default)

```bash
curl "http://localhost:8000/realtime/forecast/daily"
```

**Response:** 24-hour temperature forecast

---

### Test 2: Daily Humidity Forecast

```bash
curl "http://localhost:8000/realtime/forecast/daily?metric=humidity"
```

**Response:** 24-hour humidity forecast

---

### Test 3: Weekly Temperature (RNN Model)

```bash
curl "http://localhost:8000/realtime/forecast/weekly?model_type=rnn"
```

**Response:** 7-day temperature forecast with day labels

---

### Test 4: Monthly PM2.5 Forecast

```bash
curl "http://localhost:8000/realtime/forecast/monthly?metric=pm25&days=90"
```

**Response:** 30-day PM2.5 forecast

---

### Test 5: CO2 Forecast for Specific Date

```bash
curl "http://localhost:8000/realtime/forecast/monthly?metric=co2&ref_date=2025-11-01"
```

**Response:** 30-day CO2 forecast starting from Nov 1

---

## 3. View Cache Status

```bash
# Check cache files
ls -lh /tmp/bima_forecast_models/

# View cache metadata
cat /tmp/bima_forecast_models/metadata.json | jq .
```

**Output example:**

```json
{
  "daily_temp_lstm": {
    "data_hash": "3f8a2c7d...",
    "data_length": 72,
    "trained_at": "2025-11-27T15:30:00",
    "model_type": "lstm",
    "granularity": "daily",
    "metric": "temp"
  }
}
```

---

## 4. How Data Updates Work

### Same Day (Cache Hit)

```bash
# First request (11:00 AM) - Train model
curl "http://localhost:8000/realtime/forecast/daily"
# Time: ~2 seconds (train + inference)

# Second request (11:05 AM) - Load from cache
curl "http://localhost:8000/realtime/forecast/daily"
# Time: ~100ms (cache load only)
```

### Next Day (New Data Available)

```bash
# Third request (next day) - Data changed, retrain
curl "http://localhost:8000/realtime/forecast/daily"
# Time: ~2 seconds (new model train + inference)
# Cache automatically updated!
```

---

## 5. All Available Query Parameters

### Daily Forecast

```bash
curl "http://localhost:8000/realtime/forecast/daily?model_type=LSTM&metric=METRIC&hours=HOURS&ref_datetime=DATETIME"
```

| Parameter      | Options                               | Default | Example             |
| -------------- | ------------------------------------- | ------- | ------------------- |
| `model_type`   | lstm, rnn                             | lstm    | lstm                |
| `metric`       | temp, humidity, wind_speed, pm25, co2 | temp    | temp                |
| `hours`        | 24-240                                | 72      | 72                  |
| `ref_datetime` | ISO format                            | now     | 2025-11-27T15:30:00 |

### Weekly Forecast

```bash
curl "http://localhost:8000/realtime/forecast/weekly?model_type=LSTM&metric=METRIC&days=DAYS&ref_date=DATE"
```

| Parameter    | Options                               | Default | Example    |
| ------------ | ------------------------------------- | ------- | ---------- |
| `model_type` | lstm, rnn                             | lstm    | lstm       |
| `metric`     | temp, humidity, wind_speed, pm25, co2 | temp    | temp       |
| `days`       | 14-90                                 | 30      | 30         |
| `ref_date`   | YYYY-MM-DD                            | today   | 2025-11-20 |

### Monthly Forecast

```bash
curl "http://localhost:8000/realtime/forecast/monthly?model_type=LSTM&metric=METRIC&days=DAYS&ref_date=DATE"
```

| Parameter    | Options                               | Default | Example    |
| ------------ | ------------------------------------- | ------- | ---------- |
| `model_type` | lstm, rnn                             | lstm    | lstm       |
| `metric`     | temp, humidity, wind_speed, pm25, co2 | temp    | temp       |
| `days`       | 30-365                                | 90      | 90         |
| `ref_date`   | YYYY-MM-DD                            | today   | 2025-11-01 |

---

## 6. Common Use Cases

### Weather Dashboard

```bash
# Get all 3 forecasts for dashboard
curl "http://localhost:8000/realtime/forecast/daily?metric=temp"
curl "http://localhost:8000/realtime/forecast/weekly?metric=temp"
curl "http://localhost:8000/realtime/forecast/monthly?metric=temp"
```

### Air Quality Monitoring

```bash
# PM2.5 forecasts
curl "http://localhost:8000/realtime/forecast/daily?metric=pm25"
curl "http://localhost:8000/realtime/forecast/weekly?metric=pm25"
curl "http://localhost:8000/realtime/forecast/monthly?metric=pm25"
```

### Indoor Comfort Analysis

```bash
# Temperature + Humidity + CO2
curl "http://localhost:8000/realtime/forecast/daily?metric=temp"
curl "http://localhost:8000/realtime/forecast/daily?metric=humidity"
curl "http://localhost:8000/realtime/forecast/monthly?metric=co2"
```

### Custom Historical Training

```bash
# Use more historical data for training (more accurate)
curl "http://localhost:8000/realtime/forecast/monthly?metric=temp&days=180"
curl "http://localhost:8000/realtime/forecast/monthly?metric=temp&days=365"
```

---

## 7. Testing with Python

```python
import requests
import json

BASE_URL = "http://localhost:8000/realtime"

# Get daily forecast
response = requests.get(f"{BASE_URL}/forecast/daily?metric=temp")
data = response.json()

print(f"Granularity: {data['granularity']}")
print(f"Metric: {data['metric']}")
print(f"Model: {data['model_used']}")
print(f"Forecast hours: {len(data['forecast'])}")
print(f"First 5 values: {data['forecast'][:5]}")
print(f"Training datapoints: {data['training_datapoints']}")
```

---

## 8. Clear Cache (Force Retrain)

```bash
# Remove all cached models
rm -rf /tmp/bima_forecast_models/

# Next request will retrain all models
curl "http://localhost:8000/realtime/forecast/daily"
```

---

## 9. Monitor Performance

### Check inference speed

```bash
time curl "http://localhost:8000/realtime/forecast/daily"
# Should be ~100ms if cached, 2-5s if training
```

### Check cache hit rate

```bash
# Request same endpoint multiple times
for i in {1..5}; do
  echo "Request $i:"
  time curl -s "http://localhost:8000/realtime/forecast/daily" | grep model_used
done
# First should be slow, rest should be fast (~100ms)
```

---

## 10. Database Check

Verify data availability in sensor_hourly:

```bash
# Connect to PostgreSQL
psql -h localhost -U postgres -d smartbuilding

# Check latest data
SELECT COUNT(*), MIN(ts), MAX(ts)
FROM sensor_hourly
WHERE ts > NOW() - INTERVAL '90 days';

# Check specific metric
SELECT COUNT(*), AVG(temp), MIN(temp), MAX(temp)
FROM sensor_hourly
WHERE ts > NOW() - INTERVAL '7 days' AND temp IS NOT NULL;
```

---

## ⚠️ Troubleshooting

### Error: "Data tidak cukup"

```
Solution: Increase the `hours` or `days` parameter
curl "http://localhost:8000/realtime/forecast/daily?hours=120"
```

### Error: "Tidak ada data untuk forecast"

```
Solution: Check if sensor_hourly has data for the requested period
SELECT COUNT(*) FROM sensor_hourly WHERE ts > NOW() - INTERVAL '72 hours';
```

### Models not loading from cache

```
Solution: Clear cache and retrain
rm -rf /tmp/bima_forecast_models/
curl "http://localhost:8000/realtime/forecast/daily"
```

### Memory issues

```
Solution: The models are small (CPU-optimized), but if issues persist:
- Kill old processes: pkill -f "uvicorn"
- Restart server: uvicorn app.main:app --reload
```

---

## 📖 More Information

- **Full API Documentation**: See `FORECAST_API.md`
- **Implementation Details**: See `FORECAST_IMPLEMENTATION.md`
- **Run Tests**: `python test_forecast.py`

---

**Ready to forecast!** 🎯
