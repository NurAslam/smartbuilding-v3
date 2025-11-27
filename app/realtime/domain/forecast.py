"""
Forecasting module untuk daily, weekly, dan monthly predictions.
Menggunakan LSTM dan SimpleRNN yang dioptimasi untuk CPU (stateless, layer minimal).

Data source: sensors_hourly (real monitoring data)
Automatic update: Model dilatih ulang setiap data baru tersedia
Persistence: Model disimpan ke disk dan di-load ulang

Catatan:
- Models: SimpleLSTM (1 layer LSTM ringan) dan SimpleRNN
- Input: time-series historis dari database (hourly data aggregated)
- Output: forecast untuk N jam/hari/bulan ke depan
- Optimization: stateless, kecil ukuran, cepat inference
- Data update: Otomatis dari database setiap forecast request
"""

import numpy as np
from datetime import datetime, timedelta
import pickle
import os
import json
import hashlib
from typing import Dict, List, Tuple, Optional

# TensorFlow/Keras dengan optimasi CPU
import tensorflow as tf
from tensorflow.keras import Sequential
from tensorflow.keras.layers import LSTM, SimpleRNN, Dense, Dropout
from tensorflow.keras.optimizers import Adam
from sklearn.preprocessing import MinMaxScaler


# ======================== Config ========================
FORECAST_CACHE_DIR = "/tmp/bima_forecast_models"
os.makedirs(FORECAST_CACHE_DIR, exist_ok=True)

# Model hyperparameter (ringan untuk CPU)
LSTM_UNITS = 32  # Small for CPU
RNN_UNITS = 32
DROPOUT_RATE = 0.1
LOOK_BACK = 7  # 7 step lookback (jam/hari)
BATCH_SIZE = 16

# Cache metadata untuk tracking updates
CACHE_METADATA_PATH = os.path.join(FORECAST_CACHE_DIR, "metadata.json")


# ======================== Cache Management ========================

def _get_data_hash(data: np.ndarray) -> str:
    """Generate hash dari data untuk tracking changes."""
    return hashlib.md5(data.tobytes()).hexdigest()


def _save_model_cache(
    model_type: str,
    granularity: str,
    metric: str,
    model: Sequential,
    scaler: MinMaxScaler,
    data_hash: str,
    data_length: int,
):
    """Simpan model dan metadata ke disk."""
    cache_key = f"{granularity}_{metric}_{model_type}"
    model_path = os.path.join(FORECAST_CACHE_DIR, f"{cache_key}_model.h5")
    scaler_path = os.path.join(FORECAST_CACHE_DIR, f"{cache_key}_scaler.pkl")
    
    # Simpan model
    model.save(model_path, save_format='h5')
    
    # Simpan scaler
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
    
    # Update metadata
    metadata = {}
    if os.path.exists(CACHE_METADATA_PATH):
        with open(CACHE_METADATA_PATH, 'r') as f:
            metadata = json.load(f)
    
    metadata[cache_key] = {
        "data_hash": data_hash,
        "data_length": data_length,
        "trained_at": datetime.now(tz=None).isoformat(),
        "model_type": model_type,
        "granularity": granularity,
        "metric": metric,
    }
    
    with open(CACHE_METADATA_PATH, 'w') as f:
        json.dump(metadata, f, indent=2)


def _load_model_cache(
    model_type: str,
    granularity: str,
    metric: str,
    data_hash: str,
) -> Optional[Tuple[Sequential, MinMaxScaler]]:
    """Load model dari cache jika ada dan data_hash cocok."""
    if not os.path.exists(CACHE_METADATA_PATH):
        return None
    
    with open(CACHE_METADATA_PATH, 'r') as f:
        metadata = json.load(f)
    
    cache_key = f"{granularity}_{metric}_{model_type}"
    if cache_key not in metadata:
        return None
    
    # Check if data hash matches (data belum berubah)
    if metadata[cache_key].get("data_hash") != data_hash:
        return None
    
    try:
        cache_key = f"{granularity}_{metric}_{model_type}"
        model_path = os.path.join(FORECAST_CACHE_DIR, f"{cache_key}_model.h5")
        scaler_path = os.path.join(FORECAST_CACHE_DIR, f"{cache_key}_scaler.pkl")
        
        if not os.path.exists(model_path) or not os.path.exists(scaler_path):
            return None
        
        # Load model
        model = tf.keras.models.load_model(model_path)
        
        # Load scaler
        with open(scaler_path, 'rb') as f:
            scaler = pickle.load(f)
        
        return model, scaler
    except Exception:
        return None


# ======================== Data Preparation ========================

def prepare_timeseries(values: np.ndarray, look_back: int = LOOK_BACK) -> Tuple[np.ndarray, np.ndarray]:
    """
    Prepare time-series data untuk supervised learning.
    
    Args:
        values: 1D array dari values
        look_back: number of previous timesteps to use as variables
        
    Returns:
        (X, y) dimana X shape (n_samples, look_back) dan y shape (n_samples,)
    """
    X, y = [], []
    for i in range(len(values) - look_back):
        X.append(values[i:i + look_back])
        y.append(values[i + look_back])
    return np.array(X), np.array(y)


def normalize_data(data: np.ndarray) -> Tuple[np.ndarray, MinMaxScaler]:
    """Normalize data menggunakan MinMaxScaler."""
    scaler = MinMaxScaler(feature_range=(0, 1))
    normalized = scaler.fit_transform(data.reshape(-1, 1)).flatten()
    return normalized, scaler


def denormalize_data(normalized_data: np.ndarray, scaler: MinMaxScaler) -> np.ndarray:
    """Denormalize data kembali ke skala original."""
    return scaler.inverse_transform(normalized_data.reshape(-1, 1)).flatten()


# ======================== Model Building ========================

def build_lstm_model(look_back: int = LOOK_BACK) -> Sequential:
    """
    Build lightweight LSTM model untuk CPU.
    Single layer LSTM dengan dropout untuk regularisasi.
    """
    model = Sequential([
        LSTM(units=LSTM_UNITS, input_shape=(look_back, 1), return_sequences=False),
        Dropout(DROPOUT_RATE),
        Dense(units=16, activation="relu"),
        Dense(units=1)
    ])
    model.compile(optimizer=Adam(learning_rate=0.001), loss="mse")
    return model


def build_rnn_model(look_back: int = LOOK_BACK) -> Sequential:
    """
    Build lightweight SimpleRNN model untuk CPU.
    Single layer RNN dengan dropout.
    """
    model = Sequential([
        SimpleRNN(units=RNN_UNITS, input_shape=(look_back, 1), return_sequences=False),
        Dropout(DROPOUT_RATE),
        Dense(units=16, activation="relu"),
        Dense(units=1)
    ])
    model.compile(optimizer=Adam(learning_rate=0.001), loss="mse")
    return model


# ======================== Training ========================

def train_forecast_model(
    data: np.ndarray,
    model_type: str = "lstm",
    granularity: str = "daily",
    metric: str = "temp",
    look_back: int = LOOK_BACK,
    epochs: int = 20,
    verbose: int = 0,
    force_retrain: bool = False,
) -> Tuple[Sequential, MinMaxScaler]:
    """
    Train LSTM atau RNN model pada historical data.
    Automatic caching: jika data tidak berubah, load dari cache.
    
    Args:
        data: 1D array dari historical values
        model_type: "lstm" atau "rnn"
        granularity: "daily", "weekly", "monthly" (untuk cache key)
        metric: metric name (untuk cache key)
        look_back: lookback period
        epochs: training epochs
        verbose: verbosity level
        force_retrain: bypass cache dan train ulang
        
    Returns:
        (trained_model, scaler)
    """
    data_hash = _get_data_hash(data)
    
    # Cek cache terlebih dahulu (kecuali force_retrain)
    if not force_retrain:
        cached = _load_model_cache(model_type, granularity, metric, data_hash)
        if cached is not None:
            return cached
    
    # Normalize
    normalized_data, scaler = normalize_data(data)
    
    # Prepare sequences
    X, y = prepare_timeseries(normalized_data, look_back)
    X = X.reshape((X.shape[0], X.shape[1], 1))  # (samples, timesteps, features)
    
    # Build model
    if model_type == "lstm":
        model = build_lstm_model(look_back)
    elif model_type == "rnn":
        model = build_rnn_model(look_back)
    else:
        raise ValueError("model_type harus 'lstm' atau 'rnn'")
    
    # Train
    model.fit(X, y, epochs=epochs, batch_size=BATCH_SIZE, verbose=verbose)
    
    # Simpan ke cache
    _save_model_cache(model_type, granularity, metric, model, scaler, data_hash, len(data))
    
    return model, scaler


# ======================== Forecasting ========================

def forecast_ahead(
    model: Sequential,
    scaler: MinMaxScaler,
    last_sequence: np.ndarray,
    steps_ahead: int,
) -> np.ndarray:
    """
    Generate forecast untuk N steps ke depan.
    
    Args:
        model: trained keras model
        scaler: MinMaxScaler yang digunakan saat training
        last_sequence: normalized sequence terakhir (shape: (look_back,))
        steps_ahead: number of steps to forecast
        
    Returns:
        forecast values dalam skala original (shape: (steps_ahead,))
    """
    forecasts = []
    current_seq = last_sequence.copy()
    
    for _ in range(steps_ahead):
        # Reshape untuk prediction
        X_pred = current_seq.reshape(1, len(current_seq), 1)
        next_val = model.predict(X_pred, verbose=0)[0][0]
        forecasts.append(next_val)
        
        # Update sequence: drop first, append predicted
        current_seq = np.append(current_seq[1:], next_val)
    
    forecasts_normalized = np.array(forecasts)
    forecasts_original = denormalize_data(forecasts_normalized, scaler)
    
    return forecasts_original


def forecast_daily(
    hourly_data: np.ndarray,
    metric: str = "temp",
    model_type: str = "lstm",
) -> Dict[str, any]:
    """
    Forecast 24 jam ke depan dari hourly data.
    Automatic update: jika ada data baru dari database, model akan retrain.
    
    Args:
        hourly_data: array of last 24-72 hours of data
        metric: nama metric (untuk logging dan cache key)
        model_type: "lstm" atau "rnn"
        
    Returns:
        {
            "metric": str,
            "granularity": "daily",
            "forecast_hours": 24,
            "forecast": [...],
            "model_used": str,
            "cache_status": "loaded" atau "retrained"
        }
    """
    # Ensure minimum data
    if len(hourly_data) < LOOK_BACK:
        raise ValueError(f"Data harus minimal {LOOK_BACK} data points")
    
    # Train model (dengan caching otomatis)
    model, scaler = train_forecast_model(
        hourly_data,
        model_type=model_type,
        granularity="daily",
        metric=metric,
        epochs=10
    )
    
    # Get last sequence (normalized)
    normalized_data, _ = normalize_data(hourly_data)
    last_seq = normalized_data[-LOOK_BACK:]
    
    # Forecast 24 hours
    forecast_values = forecast_ahead(model, scaler, last_seq, steps_ahead=24)
    
    # Cleanup
    del model
    tf.keras.backend.clear_session()
    
    return {
        "metric": metric,
        "granularity": "daily",
        "forecast_hours": 24,
        "forecast": forecast_values.tolist(),
        "model_used": model_type.upper(),
    }


def forecast_weekly(
    daily_data: np.ndarray,
    metric: str = "temp",
    model_type: str = "lstm",
) -> Dict[str, any]:
    """
    Forecast 7 hari ke depan dari daily aggregated data.
    Automatic update: jika ada data hari baru, model akan retrain.
    
    Args:
        daily_data: array of last 14-30 days of daily data
        metric: nama metric (untuk logging dan cache key)
        model_type: "lstm" atau "rnn"
        
    Returns:
        {
            "metric": str,
            "granularity": "weekly",
            "forecast_days": 7,
            "forecast": [...],
            "model_used": str,
        }
    """
    # Ensure minimum data
    if len(daily_data) < LOOK_BACK:
        raise ValueError(f"Data harus minimal {LOOK_BACK} data points")
    
    # Train model (dengan caching otomatis)
    model, scaler = train_forecast_model(
        daily_data,
        model_type=model_type,
        granularity="weekly",
        metric=metric,
        epochs=15
    )
    
    # Get last sequence (normalized)
    normalized_data, _ = normalize_data(daily_data)
    last_seq = normalized_data[-LOOK_BACK:]
    
    # Forecast 7 days
    forecast_values = forecast_ahead(model, scaler, last_seq, steps_ahead=7)
    
    # Cleanup
    del model
    tf.keras.backend.clear_session()
    
    return {
        "metric": metric,
        "granularity": "weekly",
        "forecast_days": 7,
        "forecast": forecast_values.tolist(),
        "model_used": model_type.upper(),
    }



def forecast_monthly(
    monthly_data: np.ndarray,
    metric: str = "temp",
    model_type: str = "lstm",
) -> Dict[str, any]:
    """
    Forecast 30 hari ke depan dari monthly data (atau daily dalam range bulan).
    Automatic update: model di-retrain setiap ada data hari baru di bulan.
    
    Args:
        monthly_data: array of last 2-3 months of daily data
        metric: nama metric
        model_type: "lstm" atau "rnn"
        
    Returns:
        {
            "metric": str,
            "granularity": "monthly",
            "forecast_days": 30,
            "forecast": [...]
        }
    """
    if len(monthly_data) < LOOK_BACK:
        raise ValueError(f"Data harus minimal {LOOK_BACK} data points")
    
    model, scaler = train_forecast_model(
        monthly_data,
        model_type=model_type,
        granularity="monthly",
        metric=metric,
        epochs=20
    )
    
    normalized_data, _ = normalize_data(monthly_data)
    last_seq = normalized_data[-LOOK_BACK:]
    
    forecast_values = forecast_ahead(model, scaler, last_seq, steps_ahead=30)
    
    del model
    tf.keras.backend.clear_session()
    
    return {
        "metric": metric,
        "granularity": "monthly",
        "forecast_days": 30,
        "forecast": forecast_values.tolist(),
        "model_used": model_type.upper(),
    }
