# Smart Building BIMA

## 1) Prasyarat

- Python 3.10+
- PostgreSQL (buat DB sesuai `.env`)
- (Opsional) venv

---

## 2) Setup & Jalankan (Step-by-step)

1. **Clone / copy** proyek ini
2. **Buat virtual env & install deps**

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Siapkan .env**

   ```bash
   cp .env.example .env
   # Edit DB_HOST/PORT/NAME/USER/PASS, APP_TZ, dll.
   ```

4. **Pastikan DB siap**

   - Buat database sesuai `.env` (mis. `smartbuilding`)
   - Tabel akan dibuat otomatis saat startup

5. **Jalankan dev server**

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

6. **Cek health**

   - `GET http://localhost:8000/status`
   - `GET http://localhost:8000/realtime/sensor/status`
   - `GET http://localhost:8000/simulation/status`

### Menjalankan di Production (satu proses)

Gunakan gunicorn + uvicorn worker:

```bash
gunicorn -k uvicorn.workers.UvicornWorker -w 1 -b 0.0.0.0:8000 app.main:app
```

> **Penting:** Scheduler realtime akan **jalan di setiap proses**. Jalankan **1 worker** saja untuk mencegah double insert, atau pisahkan scheduler ke service terpisah.

---

## 3) Scheduler Realtime (otomatis isi data per jam)

- Scheduler dijalankan via `AsyncIOScheduler` pada **startup**.
- Insert otomatis **setiap jam tepat :00 WIB**.

Cek status:

```
GET /realtime/sensor/scheduler-status
```

Respon harus `running: true` dan ada job `hourly_gen` dengan `next_run_time`.

> Untuk uji cepat, Anda bisa (sementara) ubah trigger menjadi setiap menit di `setup_scheduler()`:
> `CronTrigger(minute="*/1", second=0, ...)` lalu kembalikan ke `minute=0`.

---

## 4) Endpoint API untuk Frontend

### A. Simulation

#### 1) `GET /simulation/status`

Health check.

#### 2) `GET /simulation/list-ceiling`

Daftar pilihan konstruksi/ceiling.

#### 3) `GET /simulation/surface-comfort`

Hitung suhu permukaan (AC & NON_AC) + comfort index sederhana.
Query params:

- `T_out` (float) — outdoor °C
- `T_in` (float) — indoor °C
- `humidity` (float, default 50) — %
- `wind_speed` (float, default 0) — m/s
- `ceiling` (str) — nama konstruksi (alias didukung)

Contoh:

```
GET /simulation/surface-comfort?T_out=33&T_in=24&humidity=60&wind_speed=0.5&ceiling=SGU%20Window%20(Shaded)
```

#### 4) `POST /simulation/analyze`

Upload CSV & latih model. **Form-data (multipart)**:

- `file` (CSV) — kolom minimal: `temp,humidity,wind_speed,pm2_5` (opsional: `date, EnergyConsumption, SquareFootage`)
- `building_name` (str)
- `latitude` (float), `longitude` (float)
- `ceiling` (str) — nama/alias valid dari `/simulation/list-ceiling`
- `ac_mode` (`AC`|`NON_AC`, default `AC`)
- `model_selection_metric` (`RMSE`|`MSE`|`MAPE`, default `RMSE`)
- `persist` (bool, default `true`)

Response (ringkas):

```json
{
  "feature_cols": ["temp","humidity","wind_speed","pm2_5","surface_temp"],
  "metrics": {"RF": {...},"XGB": {...},"SVR": {...},"LSTM": {...}},
  "chosen_model": "XGB",
  "chosen_metric": "RMSE",
  "model_id": "uuid-..."
}
```

#### 5) `POST /simulation/predict`

**(Sudah diubah)**: `comfort` ➜ `ppv` dan ditambah `ppd`.

Body (JSON):

```json
{
  "temp": 26.5,
  "humidity": 60,
  "wind_speed": 1.2,
  "pm2_5": 25,
  "model_id": "uuid-optional"
}
```

Response:

```json
{
  "model_used": "XGB",
  "ppv": 1, // sebelumnya: "comfort"
  "ppd": 26.12, // % ketidakpuasan (Fanger)
  "energy_kwh": 77.8244,
  "cost_idr": 86753.96,
  "model_id": "15f57ef7-a620-4512-bcc1-72091409cf2d",
  "building_info": {
    "name": "SGU Window (Shaded)",
    "lat": 12,
    "lon": 24,
    "jenis_ceiling": "SGU Window (Shaded)",
    "ac_mode": "AC"
  }
}
```

#### 6) `GET /simulation/models`

List model tersimpan.

#### 7) `GET /simulation/models/{model_id}`

Detail model.

#### 8) `DELETE /simulation/models/{model_id}`

Hapus artifacts model.

---

### B. Realtime

#### 1) `GET /realtime/sensor/status`

Info versi & TZ.

#### 2) `POST /realtime/sensor/generate-now`

Insert **satu** baris data synthetik untuk jam sekarang (WIB).

> Untuk testing manual.

#### 3) `GET /realtime/sensor/latest?n=50`

Ambil N baris terakhir (paling baru → lama), cocok untuk **live table** / sparkline.

#### 4) `GET /realtime/sensor/scheduler-status`

Pantau scheduler (running & jadwal job).

#### 5) `GET /realtime/sensor/summary/daily|weekly|monthly`

Ringkasan agregat (total energi, biaya, PPD rata-rata, dsb) untuk jangka waktu terkait.
Opsional `ref_date=YYYY-MM-DD` (WIB).

#### 6) `GET /realtime/sensor/series/daily|weekly|monthly`

**Direkomendasikan untuk grafik**: deret waktu ter-agregasi berdasarkan bucket (harian/mingguan/bulanan).

**Query params:**

- `daily`: `days` (default 30), `ref_date` (opsional)
- `weekly`: `weeks` (default 12), `ref_date` (opsional)
- `monthly`: `months` (default 12), `ref_date` (opsional)

**Response contoh (`/series/daily?days=7`):**

```json
{
  "granularity": "daily",
  "start_wib": "2025-09-19T00:00:00+07:00",
  "end_wib": "2025-09-26T00:00:00+07:00",
  "rows": [
    {
      "ts_start": "2025-09-19T00:00:00+07:00",
      "avg_temp": 26.4,
      "avg_humidity": 67.2,
      "avg_wind_speed": 3.1,
      "avg_pm25": 18.5,
      "total_energy_kwh": 123.45,
      "total_cost_idr": 137600.0,
      "avg_pmv": 0.2,
      "avg_ppd": 8.9,
      "eui_kwh_m2": 0.0823,
      "count": 24
    }
  ],
  "meta": { "tariff_idr_per_kwh": 1114.74, "floor_area_m2": 1500 }
}
```

**Tips untuk FE grafik**:

- Sumbu-X: `ts_start` (WIB ISO string)
- Pilih metrik sesuai grafik: `total_energy_kwh` (bar/area), `avg_temp` & `avg_pm25` (line), `avg_ppd` (line).
- `count` = jumlah titik mentah per bucket (harian biasanya 24 jam).

---

#### 7) Forecast Endpoints (NEW) - LSTM/RNN Predictions

Endpoint untuk forecast cuaca/metrik 7-30 hari ke depan menggunakan **LSTM neural networks**. Data source dari `sensor_hourly` tabel (real monitoring data). Model otomatis di-retrain setiap ada data baru.

##### A. `GET /realtime/forecast/daily`

**Forecast 24 jam ke depan** dari hourly historical data (jam-jaman).

**Query params:**

- `model_type` (str, default `lstm`) — `lstm` atau `rnn`
- `metric` (str, default `temp`) — `temp`, `humidity`, `wind_speed`, `pm25`, `co2`
- `hours` (int, default 72) — Historical hours untuk training (min 24, max 240)
- `ref_datetime` (ISO format, optional) — Reference datetime (default: sekarang)

**Example:**

```bash
GET /realtime/forecast/daily?model_type=lstm&metric=temp&hours=72
```

**Response:**

```json
{
  "metric": "temp",
  "granularity": "daily",
  "forecast_hours": 24,
  "forecast": [24.33, 24.44, 24.52, ..., 26.12],
  "forecast_with_timestamps": [
    {"timestamp": "2025-11-27T14:41:06.545471+07:00", "value": 24.33},
    {"timestamp": "2025-11-27T15:41:06.545471+07:00", "value": 24.44},
    ...
  ],
  "model_used": "LSTM",
  "ref_datetime": "2025-11-27T14:41:06.545471+07:00",
  "forecast_start": "2025-11-27T14:41:06.545471+07:00",
  "forecast_end": "2025-11-28T14:41:06.545471+07:00",
  "training_datapoints": 71
}
```

##### B. `GET /realtime/forecast/weekly`

**Forecast 7 hari ke depan** dari daily aggregated data.

**Query params:**

- `model_type` (str, default `lstm`) — `lstm` atau `rnn`
- `metric` (str, default `temp`) — `temp`, `humidity`, `wind_speed`, `pm25`, `co2`
- `days` (int, default 30) — Historical days untuk training (min 14, max 90)
- `ref_date` (ISO date format, optional) — Reference date (default: hari ini)

**Example:**

```bash
GET /realtime/forecast/weekly?model_type=lstm&metric=temp&days=30
```

**Response:**

```json
{
  "metric": "temp",
  "granularity": "weekly",
  "forecast_days": 7,
  "forecast": [25.3, 24.8, 23.9, 22.5, 21.8, 22.3, 23.5],
  "forecast_with_timestamps": [
    {"timestamp": "2025-11-28", "value": 25.3},
    {"timestamp": "2025-11-29", "value": 24.8},
    ...
  ],
  "model_used": "LSTM",
  "ref_date": "2025-11-27",
  "forecast_start": "2025-11-27",
  "forecast_end": "2025-12-04",
  "training_datapoints": 30
}
```

##### C. `GET /realtime/forecast/monthly`

**Forecast 30 hari ke depan** dari daily aggregated data.

**Query params:**

- `model_type` (str, default `lstm`) — `lstm` atau `rnn`
- `metric` (str, default `temp`) — `temp`, `humidity`, `wind_speed`, `pm25`, `co2`
- `days` (int, default 90) — Historical days untuk training (min 30, max 365)
- `ref_date` (ISO date format, optional) — Reference date (default: hari ini)

**Example:**

```bash
GET /realtime/forecast/monthly?model_type=lstm&metric=temp&days=90
```

**Response:**

```json
{
  "metric": "temp",
  "granularity": "monthly",
  "forecast_days": 30,
  "forecast": [26.07, 26.06, 26.02, ..., 26.33],
  "forecast_with_timestamps": [
    {"timestamp": "2025-11-28", "value": 26.07},
    {"timestamp": "2025-11-29", "value": 26.06},
    ...
  ],
  "model_used": "LSTM",
  "ref_date": "2025-11-27",
  "forecast_start": "2025-11-27",
  "forecast_end": "2025-12-27",
  "training_datapoints": 152
}
```

**Catatan Penting:**

- **Data source**: `sensor_hourly` tabel (real monitoring data dari database)
- **Model**: LSTM atau SimpleRNN (32 units, optimized untuk CPU)
- **Lookback window**: 7 timesteps (7 jam untuk daily, 7 hari untuk weekly/monthly)
- **Caching**: Model otomatis disimpan ke `/tmp/bima_forecast_models/` dan di-reload jika data belum berubah
- **Training**: Epochs 10-20 tergantung granularity, otomatis retrain jika data berubah
- **Normalization**: MinMaxScaler (0-1 range), denormalized pada output
- **Forecast method**: Recursive (auto-regressive) — setiap prediksi menjadi input untuk prediksi berikutnya

---

## 5) Rumus & Metodologi

### 5.1. PPV & PPD

- **PPV** (Predicted **P**erception **V**ote): di endpoint `/simulation/predict`, PPV adalah output model ML yang telah **dibulatkan** ke integer rentang `[-3, +3]`.
- **PPD** (Predicted Percentage of Dissatisfied) — rumus Fanger (ASHRAE 55 / ISO 7730):

  $$
  \text{PPD} = 100 - 95 \cdot e^{-0.03353 \cdot \text{PMV}^4 - 0.2179 \cdot \text{PMV}^2}
  $$

  (Pada backend, PPV diperlakukan setara dengan PMV untuk menghitung PPD.)

  **Nilai PPD referensi:**

  - PMV = 0 → **5.00%**

  - PMV = ±1 → **26.12%**

  - PMV = ±2 → **76.76%**

  - PMV = ±3 → **99.12%**

  > **Menjawab pertanyaanmu:** “nilai pmv yang **-3** itu berapa?”
  > PMV = **-3** (sangat dingin). PPD ≈ **99.12%** (hampir semua tidak puas).

### 5.2. PMV Diskrit (Realtime generator)

Fungsi `temp_to_pmv(temp_c)` memakai band suhu (WIB):

- `temp ≤ 16` → PMV = **-3**
- `≤ 18` → **-2**
- `≤ 20` → **-1**
- `≤ 24` → **0**
- `≤ 28` → **+1**
- `≤ 32` → **+2**
- `> 32` → **+3**

Label:

- -3: sangat dingin, -2: dingin, -1: agak dingin, 0: netral, +1: agak panas, +2: panas, +3: sangat panas

**PPD** dihitung dari PMV di atas dengan rumus Fanger (hasilnya “berundak” karena PMV diskrit).

### 5.3. Comfort Index Sederhana (endpoint `/simulation/surface-comfort`)

Untuk indeks sederhana (bukan ML), dipakai:

$$
t_\text{eff} = T_{in} + 0.02 \cdot (RH - 50) - 0.5 \cdot \min(\text{wind}, 2)
$$

$$
\text{ComfortIndex} = \text{clamp}\left(\frac{t_\text{eff} - 24}{2}, -3, 3\right)
$$

Lalu dibulatkan ke label yang sama seperti PMV diskrit.

### 5.4. Surface Temperature

- **AC-influenced**:

  $$
  T_\text{surface,AC} = T_\text{base,AC} + \beta \cdot (T_{in} - 24)
  $$

- **NON-AC / Outdoor-influenced**:

  $$
  T_\text{surface,NONAC} = T_\text{base,NONAC} + \beta \cdot (T_{out} - 32)
  $$

Dengan tabel `T_base`/`β` per jenis konstruksi (lihat `/simulation/list-ceiling`). Default `β = 1.0`.

### 5.5. Target Training (Comfort gabungan, untuk model ML)

Saat `/simulation/analyze`, dibuat target **kontinu** `[-3, +3]` dari kombinasi suhu, kelembapan, angin, PM2.5:

- Normalisasi:

  - `temp_hot  = clip01((temp - 27) / 6)`
  - `temp_cold = clip01((20 - temp) / 5)`
  - `humidity_dev = clip01(|RH - 50| / 30)`
  - `pm_norm = clip01(pm / 150)`
  - `wind_norm = clip01(wind / 8)`

- Efek angin: `- wind_norm * temp_hot + wind_norm * temp_cold`
- Bobot: `w_temp=0.5, w_hum=0.2, w_wind=0.15, w_pm=0.15`
- Discomfort index `DI` di-clip [0,1], lalu:

  $$
  \text{target} = 3 - 6 \cdot DI \quad (\in [-3,3])
  $$

Model (RF/XGB/SVR/LSTM) mempelajari relasi fitur ➜ target ini. Saat **predict**, output kontinu dipotong ke `[-3,3]` dan **dibulatkan** ke integer untuk **PPV**.

### 5.6. Estimasi Energi (Simulation)

- Jika file memiliki `EnergyConsumption` memadai → fit **LinearRegression**:
  `Energy ≈ a * temp + b`
- Jika tidak ada/miskin data → fallback **interpolasi linier** berdasarkan rentang suhu & rentang energi `[emin, emax]` dari data yg tersedia.
- **Biaya (IDR)**:

  $$
  \text{cost\_idr} = \text{energy\_kwh} \times \text{TARIFF\_IDR\_PER\_KWH}
  $$

- **EUI (kWh/m²)** (Realtime):

  $$
  \text{eui\_kwh\_m2} = \frac{\text{energy\_kwh}}{\text{FLOOR\_AREA\_M2}}
  $$

### 5.7. Energi Sintetis (Realtime generator)

Dipakai untuk membuat data per jam (WIB):

$$
\text{occ\_factor} =
\begin{cases}
1.0 & \text{jam kerja (Senin–Jumat, 08–18 WIB)} \\
0.35 & \text{lainnya}
\end{cases}
$$

$$
\text{base\_load} =
\begin{cases}
\text{BASE\_LOAD\_DAY} & \text{jam kerja}\\
\text{BASE\_LOAD\_NIGHT} & \text{lainnya}
\end{cases}
$$

$$
\text{ac\_work} = \max(0, temp - \text{SETPOINT\_C}) \cdot \text{AC\_COEFF} \cdot \text{occ\_factor}
$$

$$
\text{humid\_penalty} = \max(0, RH - 60) \cdot 0.003 \cdot \text{occ\_factor}
$$

$$
\text{energy\_kwh} = \max\left(0.05, \text{base\_load} + \text{ac\_work} + \text{humid\_penalty} + \mathcal{N}(0,0.05)\right)
$$

---

## 6) Contoh cURL (untuk Frontend)

**Analyze (upload CSV):**

```bash
curl -X POST "http://localhost:8000/simulation/analyze" \
  -F "file=@/path/data.csv" \
  -F "building_name=HQ" \
  -F "latitude=-6.2" \
  -F "longitude=106.8" \
  -F "ceiling=SGU Window (Shaded)" \
  -F "ac_mode=AC" \
  -F "model_selection_metric=RMSE" \
  -F "persist=true"
```

**Predict:**

```bash
curl -X POST "http://localhost:8000/simulation/predict" \
  -H "Content-Type: application/json" \
  -d '{"temp":26.5,"humidity":60,"wind_speed":1.2,"pm2_5":25,"model_id":"<uuid>"}'
```

**Latest (50 rows):**

```bash
curl "http://localhost:8000/realtime/sensor/latest?n=50"
```

**Series (harian 30 hari ke belakang):**

```bash
curl "http://localhost:8000/realtime/sensor/series/daily?days=30"
```

**Forecast Daily (24 jam ke depan):**

```bash
curl "http://localhost:8000/realtime/forecast/daily?model_type=lstm&metric=temp&hours=72"
```

**Forecast Weekly (7 hari ke depan):**

```bash
curl "http://localhost:8000/realtime/forecast/weekly?model_type=lstm&metric=temp&days=30"
```

**Forecast Monthly (30 hari ke depan):**

```bash
curl "http://localhost:8000/realtime/forecast/monthly?model_type=lstm&metric=temp&days=90"
```

---

## 7) Struktur Folder & File Penting

```
BIMA/
├── app/
│   ├── main.py                    # FastAPI app entry point
│   ├── core/
│   │   ├── config.py             # Environment & settings
│   │   └── logging.py            # Logger setup
│   ├── realtime/
│   │   ├── db.py                 # Database schema & connection
│   │   ├── generator.py          # Synthetic data generator
│   │   ├── scheduler.py          # APScheduler setup
│   │   ├── domain/
│   │   │   ├── forecast.py       # LSTM/RNN forecast models
│   │   │   └── comfort.py        # PMV/PPD calculations
│   │   └── routers/
│   │       ├── sensor.py         # Data monitoring endpoints
│   │       ├── forecast.py       # Forecast API endpoints
│   │       └── grafik.py         # Visualization data endpoints
│   └── simulation/
│       ├── domain/
│       │   ├── analysis.py       # ML model training
│       │   └── comfort.py        # Comfort calculations
│       └── routers/
│           └── analysis.py       # Simulation endpoints
├── artifacts/                     # Persisted ML models
├── .env                          # Environment variables
├── requirements.txt              # Python dependencies
└── Readme.md                     # This file
```

---

## 8) Environment Variables (.env)

```ini
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=smartbuilding
DB_USER=postgres
DB_PASS=password

# Application
APP_TZ=Asia/Jakarta
APP_DEBUG=false

# Building Info
FLOOR_AREA_M2=1500
TARIFF_IDR_PER_KWH=1114.74

# Energy Simulation
BASE_LOAD_DAY=5.0
BASE_LOAD_NIGHT=1.0
AC_COEFF=0.8
SETPOINT_C=24

# Scheduler
SCHEDULER_ENABLED=true
SCHEDULER_MINUTE=0              # Run at minute :00 every hour
```

---

## 9) Development Tips

### Testing Forecast Manually

1. **Populate database** (if empty):

   ```bash
   python populate_test_data.py
   ```

2. **Test endpoints** via cURL or Postman:

   ```bash
   # Daily (24 jam)
   curl "http://localhost:8000/realtime/forecast/daily?metric=temp&hours=72"

   # Weekly (7 hari)
   curl "http://localhost:8000/realtime/forecast/weekly?metric=temp&days=30"

   # Monthly (30 hari)
   curl "http://localhost:8000/realtime/forecast/monthly?metric=temp&days=90"
   ```

3. **Check model cache**:
   ```bash
   ls -lah /tmp/bima_forecast_models/
   ```

### Common Issues

| Issue                                   | Solution                                                                          |
| --------------------------------------- | --------------------------------------------------------------------------------- |
| "Data tidak cukup (butuh min 7 points)" | Pastikan database punya min 7 hari/jam data historis untuk granularity terkait    |
| Forecast lambat (>30s)                  | Model sedang training. Tunggu atau check `/tmp/bima_forecast_models/` untuk cache |
| "ImportError: tensorflow"               | `pip install tensorflow` (included in requirements.txt)                           |
| Scheduler tidak berjalan                | Check logs & pastikan `SCHEDULER_ENABLED=true` di `.env`                          |

---

## 10) API Health Check

Gunakan endpoint ini untuk monitoring:

```bash
# Simulation status
curl "http://localhost:8000/simulation/status"

# Realtime sensor status
curl "http://localhost:8000/realtime/sensor/status"

# Realtime scheduler status
curl "http://localhost:8000/realtime/sensor/scheduler-status"
```

Response yang sehat:

```json
{
  "version": "v0.2",
  "status": "running",
  "timestamp": "2025-11-27T14:41:06.545471+07:00"
}
```

---

**Last Updated:** 27 November 2025  
**Version:** 0.2 (with Forecast LSTM/RNN)
