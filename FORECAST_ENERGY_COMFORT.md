# Energy & Comfort Forecast Endpoints - Implementation Guide

## Overview

Added **6 new forecast endpoints** for predicting:

- **Energy Consumption (kWh)** - daily, weekly, monthly
- **Thermal Comfort (PPV/PPD)** - daily, weekly, monthly

These endpoints use LSTM/RNN models trained on historical `sensor_hourly` data.

---

## Endpoints Summary

### 1. Energy Consumption Forecast

#### Daily (24 hours ahead)

```
GET /realtime/forecast-energy/daily
```

**Query Parameters:**

- `model_type`: "lstm" or "rnn" (default: "lstm")
- `hours`: Historical hours for training (24-240, default: 72)
- `ref_datetime`: Reference datetime ISO format (default: now)

**Response Example:**

```json
{
  "metric": "energy_kwh",
  "granularity": "daily",
  "forecast_hours": 24,
  "forecast": [0.732, 0.734, 0.725, ...],
  "model_used": "LSTM",
  "ref_datetime": "2025-11-27T22:00:00+07:00",
  "forecast_start": "2025-11-27T22:00:00+07:00",
  "forecast_end": "2025-11-28T22:00:00+07:00",
  "forecast_with_timestamps": [
    {"timestamp": "2025-11-27T22:00:00+07:00", "value": 0.732},
    {"timestamp": "2025-11-27T23:00:00+07:00", "value": 0.734},
    ...
  ],
  "training_datapoints": 72
}
```

#### Weekly (7 days ahead)

```
GET /realtime/forecast-energy/weekly
```

**Query Parameters:**

- `model_type`: "lstm" or "rnn" (default: "lstm")
- `days`: Historical days for training (14-90, default: 90)
- `ref_date`: Reference date ISO format (default: today)

**Response:** 7 daily forecasts with timestamps

#### Monthly (30 days ahead)

```
GET /realtime/forecast-energy/monthly
```

**Query Parameters:**

- `model_type`: "lstm" or "rnn" (default: "lstm")
- `days`: Historical days for training (30-365, default: 90)
- `ref_date`: Reference date ISO format (default: today)

**Response:** 30 daily forecasts with timestamps

---

### 2. Thermal Comfort Forecast (PPV & PPD)

#### Daily (24 hours ahead)

```
GET /realtime/forecast-comfort/daily
```

**Query Parameters:**

- `model_type`: "lstm" or "rnn" (default: "lstm")
- `target`: "ppv" (Predicted Perception Vote) or "ppd" (Percentage Dissatisfied) (default: "ppv")
- `hours`: Historical hours for training (24-240, default: 72)
- `ref_datetime`: Reference datetime ISO format (default: now)

**PPV Scale:** -3 (sangat dingin) to +3 (sangat panas)
**PPD Scale:** 0-100 (% dissatisfied)

**Response Example:**

```json
{
  "metric": "ppv",
  "granularity": "daily",
  "forecast_hours": 24,
  "forecast": [0.59, 0.61, 0.62, ...],
  "model_used": "LSTM",
  "ref_datetime": "2025-11-27T22:00:00+07:00",
  "forecast_start": "2025-11-27T22:00:00+07:00",
  "forecast_end": "2025-11-28T22:00:00+07:00",
  "forecast_with_timestamps": [
    {"timestamp": "2025-11-27T22:00:00+07:00", "value": 0.59},
    {"timestamp": "2025-11-27T23:00:00+07:00", "value": 0.61},
    ...
  ],
  "training_datapoints": 72
}
```

#### Weekly (7 days ahead)

```
GET /realtime/forecast-comfort/weekly
```

**Query Parameters:**

- `model_type`: "lstm" or "rnn" (default: "lstm")
- `target`: "ppv" or "ppd" (default: "ppv")
- `days`: Historical days for training (14-90, default: 90)
- `ref_date`: Reference date ISO format (default: today)

**Response:** 7 daily comfort forecasts

#### Monthly (30 days ahead)

```
GET /realtime/forecast-comfort/monthly
```

**Query Parameters:**

- `model_type`: "lstm" or "rnn" (default: "lstm")
- `target`: "ppv" or "ppd" (default: "ppv")
- `days`: Historical days for training (30-365, default: 90)
- `ref_date`: Reference date ISO format (default: today)

**Response:** 30 daily comfort forecasts

---

## Usage Examples

### Energy Forecast (Daily)

```bash
curl "http://localhost:8000/realtime/forecast-energy/daily?hours=72&model_type=lstm"
```

### Energy Forecast (Weekly)

```bash
curl "http://localhost:8000/realtime/forecast-energy/weekly?days=90&model_type=lstm"
```

### Comfort Forecast (Daily - PPV)

```bash
curl "http://localhost:8000/realtime/forecast-comfort/daily?target=ppv&hours=72"
```

### Comfort Forecast (Daily - PPD)

```bash
curl "http://localhost:8000/realtime/forecast-comfort/daily?target=ppd&hours=72"
```

### Comfort Forecast (Weekly - PPD)

```bash
curl "http://localhost:8000/realtime/forecast-comfort/weekly?target=ppd&days=90"
```

### Comfort Forecast (Monthly - PPV)

```bash
curl "http://localhost:8000/realtime/forecast-comfort/monthly?target=ppv&days=365"
```

---

## Implementation Details

### Files Added/Modified

1. **NEW:** `app/realtime/routers/forecast_energy_comfort.py`

   - 6 new endpoints (3 for energy, 3 for comfort)
   - Uses same data source as monitoring: `sensor_hourly` table
   - Automatic model caching (same as environmental forecasts)

2. **MODIFIED:** `app/main.py`
   - Added imports for new routers
   - Registered comfort_router and energy_router with prefix `/realtime`

### Data Source

All forecasts use historical data from `sensor_hourly` table:

- **Energy:** `energy_kwh` column
- **PPV:** `pmv` column (aliased as ppv)
- **PPD:** `ppd` column

### Model Architecture

- **LSTM:** 32 units, 1 layer, dropout 0.1
- **RNN:** 32 units, stateless
- **Lookback window:** 7 steps
- **Batch size:** 16
- **Optimizer:** Adam

### Caching

Models are cached in `/tmp/bima_forecast_models/`:

- Each metric × model_type × granularity = separate cache file
- Cache includes: trained model (H5), scaler (pickle), metadata (JSON)
- Auto-retrains if data changes (hash-based detection)

### Performance

- **First request (cache miss):** 2-5 seconds (model training)
- **Subsequent requests (cache hit):** ~100ms (model loading only)

---

## Testing

### Test Daily Energy Forecast

```python
import requests
resp = requests.get('http://localhost:8000/realtime/forecast-energy/daily')
print(resp.json())
```

### Test Daily PPV Comfort Forecast

```python
import requests
resp = requests.get('http://localhost:8000/realtime/forecast-comfort/daily?target=ppv')
print(resp.json())
```

### Test Weekly PPD Comfort Forecast

```python
import requests
resp = requests.get('http://localhost:8000/realtime/forecast-comfort/weekly?target=ppd')
print(resp.json())
```

---

## Differences from Environmental Forecasts

| Feature          | Environmental                         | Energy & Comfort     |
| ---------------- | ------------------------------------- | -------------------- |
| Metrics          | temp, humidity, wind_speed, pm25, co2 | energy_kwh, ppv, ppd |
| Daily forecast   | 24 hours (hourly)                     | 24 hours (hourly)    |
| Weekly forecast  | 7 days (daily)                        | 7 days (daily)       |
| Monthly forecast | 30 days (daily)                       | 30 days (daily)      |
| Data source      | sensor_hourly                         | sensor_hourly        |
| Model type       | LSTM/RNN                              | LSTM/RNN             |
| Auto-update      | Yes (hash-based)                      | Yes (hash-based)     |

---

## Notes

1. **Data Requirements:**

   - Daily: min 7 hourly points (recommended 72 hours)
   - Weekly: min 7 daily points (recommended 90 days)
   - Monthly: min 7 daily points (recommended 90-365 days)

2. **PPV/PPD Values:**

   - PPV ranges from -3 (sangat dingin) to +3 (sangat panas)
   - PPD ranges from 0-100 (% of people dissatisfied)
   - Both are aggregated daily for weekly/monthly forecasts

3. **Energy Values:**

   - In kWh (kilowatt-hours)
   - Aggregated daily for weekly/monthly forecasts
   - Can be converted to cost using `TARIFF_IDR_PER_KWH` from settings

4. **Timestamp Format:**
   - Daily forecasts: ISO datetime with timezone (e.g., 2025-11-27T22:00:00+07:00)
   - Weekly/Monthly: ISO date (e.g., 2025-11-27)

---

## Frontend Integration

### Display Energy Forecast

```javascript
// Fetch data
const resp = await fetch("/realtime/forecast-energy/daily");
const data = await resp.json();

// Use forecast_with_timestamps for chart
const chart_data = {
  labels: data.forecast_with_timestamps.map((x) => x.timestamp),
  datasets: [
    {
      label: "Energy Forecast (kWh)",
      data: data.forecast_with_timestamps.map((x) => x.value),
    },
  ],
};
```

### Display Comfort Forecast

```javascript
// Fetch PPV data
const resp = await fetch("/realtime/forecast-comfort/daily?target=ppv");
const data = await resp.json();

// Map PPV to labels
const ppv_labels = {
  "-3": "Sangat Dingin",
  "-2": "Dingin",
  "-1": "Agak Dingin",
  0: "Netral (Nyaman)",
  1: "Agak Panas",
  2: "Panas",
  3: "Sangat Panas",
};

// Use forecast_with_timestamps for display
data.forecast_with_timestamps.forEach((point) => {
  console.log(
    `${point.timestamp}: PPV = ${Math.round(point.value)} (${
      ppv_labels[Math.round(point.value)]
    })`
  );
});
```

---

## Error Handling

### Common Errors

1. **400 Bad Request:** "Data tidak cukup"

   - Cause: Not enough historical data
   - Solution: Increase `hours` or `days` parameter, or wait for more data

2. **404 Not Found:** "Tidak ada data untuk forecast"

   - Cause: No data in sensor_hourly for metric
   - Solution: Ensure sensor_hourly table has data

3. **500 Internal Server Error:** Database error
   - Cause: Database connection issue
   - Solution: Check database connectivity

---

## Version & Status

- **Status:** ✅ Fully Implemented
- **Last Updated:** 27 Nov 2025
- **Version:** 0.3.0
- **Backward Compatible:** Yes (no changes to existing endpoints)
