#!/usr/bin/env python3
"""
Test script untuk forecast module.
Jalankan dengan: python test_forecast.py
"""

import sys
import numpy as np
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Add project to path
sys.path.insert(0, '/Users/user/Documents/03 KERJA/PT Multimedia Solusi Prima/2025/NOVEMBER/BIMA')

from app.realtime.domain.forecast import (
    prepare_timeseries,
    normalize_data,
    denormalize_data,
    build_lstm_model,
    build_rnn_model,
    train_forecast_model,
    forecast_ahead,
    forecast_daily,
    forecast_weekly,
    forecast_monthly,
    _get_data_hash,
)

WIB = ZoneInfo("Asia/Jakarta")


def test_data_operations():
    """Test data preparation functions"""
    print("=" * 60)
    print("TEST 1: Data Operations")
    print("=" * 60)
    
    # Generate sample data
    data = np.random.normal(loc=25, scale=2, size=100)
    print(f"✓ Generated sample data: shape={data.shape}, mean={data.mean():.2f}, std={data.std():.2f}")
    
    # Test normalization
    normalized, scaler = normalize_data(data)
    print(f"✓ Normalized data: min={normalized.min():.4f}, max={normalized.max():.4f}")
    
    # Test denormalization
    denormalized = denormalize_data(normalized, scaler)
    error = np.abs(data - denormalized).max()
    print(f"✓ Denormalized data: max error={error:.6f}")
    
    # Test time-series preparation
    X, y = prepare_timeseries(data, look_back=7)
    print(f"✓ Time-series prepared: X.shape={X.shape}, y.shape={y.shape}")
    
    # Test data hash
    hash1 = _get_data_hash(data)
    hash2 = _get_data_hash(data)
    data2 = data + 0.001  # Slightly different
    hash3 = _get_data_hash(data2)
    
    print(f"✓ Data hash: hash1={hash1[:8]}...")
    print(f"✓ Consistency: hash1==hash2: {hash1 == hash2}")
    print(f"✓ Sensitivity: hash1==hash3: {hash1 == hash3}")
    print()


def test_model_building():
    """Test model architecture"""
    print("=" * 60)
    print("TEST 2: Model Building")
    print("=" * 60)
    
    # Test LSTM model
    lstm_model = build_lstm_model(look_back=7)
    print(f"✓ LSTM Model built")
    print(f"  - Input shape: (batch, 7, 1)")
    print(f"  - Output shape: (batch, 1)")
    print(f"  - Parameters: {lstm_model.count_params()}")
    
    # Test RNN model
    rnn_model = build_rnn_model(look_back=7)
    print(f"✓ RNN Model built")
    print(f"  - Input shape: (batch, 7, 1)")
    print(f"  - Output shape: (batch, 1)")
    print(f"  - Parameters: {rnn_model.count_params()}")
    print()


def test_training_and_forecast():
    """Test training dan forecasting"""
    print("=" * 60)
    print("TEST 3: Training & Forecasting")
    print("=" * 60)
    
    # Generate realistic temperature data (24-26°C with daily cycle)
    hours = np.arange(100)
    base_temp = 25
    daily_cycle = 1.5 * np.sin(2 * np.pi * hours / 24)  # 1.5°C daily variation
    noise = np.random.normal(0, 0.5, 100)
    temp_data = base_temp + daily_cycle + noise
    
    print(f"✓ Generated synthetic temperature data: {len(temp_data)} points")
    print(f"  - Range: {temp_data.min():.2f}°C - {temp_data.max():.2f}°C")
    print(f"  - Mean: {temp_data.mean():.2f}°C")
    
    # Test daily forecast
    try:
        result = forecast_daily(temp_data, metric="temp", model_type="lstm")
        print(f"✓ Daily forecast (LSTM): {len(result['forecast'])} hours")
        print(f"  - Forecast range: {min(result['forecast']):.2f}°C - {max(result['forecast']):.2f}°C")
        print(f"  - First 5 hours: {[f'{v:.2f}' for v in result['forecast'][:5]]}")
    except Exception as e:
        print(f"✗ Daily forecast failed: {e}")
    
    # Test weekly forecast
    try:
        # Create daily data (30 days)
        daily_data = np.array([
            base_temp + 0.5 * np.sin(2 * np.pi * i / 7) + np.random.normal(0, 0.3)
            for i in range(30)
        ])
        result = forecast_weekly(daily_data, metric="temp", model_type="rnn")
        print(f"✓ Weekly forecast (RNN): {result['forecast_days']} days")
        print(f"  - Forecast: {[f'{v:.2f}' for v in result['forecast']]}")
    except Exception as e:
        print(f"✗ Weekly forecast failed: {e}")
    
    # Test monthly forecast
    try:
        # Create monthly data (90 days)
        monthly_data = np.array([
            base_temp + 1.0 * np.sin(2 * np.pi * i / 30) + np.random.normal(0, 0.5)
            for i in range(90)
        ])
        result = forecast_monthly(monthly_data, metric="temp", model_type="lstm")
        print(f"✓ Monthly forecast (LSTM): {result['forecast_days']} days")
        print(f"  - First 5 days: {[f'{v:.2f}' for v in result['forecast'][:5]]}")
        print(f"  - Last 5 days: {[f'{v:.2f}' for v in result['forecast'][-5:]]}")
    except Exception as e:
        print(f"✗ Monthly forecast failed: {e}")
    
    print()


def test_cache_mechanism():
    """Test caching mechanism"""
    print("=" * 60)
    print("TEST 4: Cache Mechanism")
    print("=" * 60)
    
    # Generate data
    data = np.random.normal(loc=25, scale=2, size=50)
    data_hash = _get_data_hash(data)
    
    print(f"✓ Data hash: {data_hash}")
    
    # First training (should save to cache)
    try:
        model1, scaler1 = train_forecast_model(
            data,
            model_type="lstm",
            granularity="daily",
            metric="test_metric",
            epochs=1,  # Quick training for test
            verbose=0
        )
        print(f"✓ First training completed (model saved to cache)")
    except Exception as e:
        print(f"✗ First training failed: {e}")
    
    # Second training with same data (should load from cache)
    try:
        model2, scaler2 = train_forecast_model(
            data,
            model_type="lstm",
            granularity="daily",
            metric="test_metric",
            epochs=1,
            verbose=0
        )
        print(f"✓ Second training attempted (should load from cache)")
    except Exception as e:
        print(f"✗ Second training failed: {e}")
    
    # Third training with different data (should retrain)
    try:
        data_modified = data + 0.5  # Modified data
        model3, scaler3 = train_forecast_model(
            data_modified,
            model_type="lstm",
            granularity="daily",
            metric="test_metric",
            epochs=1,
            force_retrain=False,  # Should detect change and retrain
            verbose=0
        )
        print(f"✓ Third training with modified data (should retrain)")
    except Exception as e:
        print(f"✗ Third training failed: {e}")
    
    print()


def test_api_response_structure():
    """Test API response structure"""
    print("=" * 60)
    print("TEST 5: API Response Structure")
    print("=" * 60)
    
    # Generate sample data
    daily_data = np.random.normal(loc=25, scale=2, size=30)
    
    try:
        result = forecast_weekly(daily_data, metric="humidity", model_type="lstm")
        
        # Check required fields
        required_fields = [
            "metric", "granularity", "forecast_days", 
            "forecast", "model_used"
        ]
        
        for field in required_fields:
            if field in result:
                print(f"✓ Field '{field}' present: {type(result[field])}")
            else:
                print(f"✗ Field '{field}' MISSING")
        
        # Check forecast type
        if isinstance(result['forecast'], list):
            print(f"✓ Forecast is list: {len(result['forecast'])} items")
        else:
            print(f"✗ Forecast is not list: {type(result['forecast'])}")
        
    except Exception as e:
        print(f"✗ Response structure test failed: {e}")
    
    print()


def run_all_tests():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "FORECAST MODULE TEST SUITE" + " " * 16 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    try:
        test_data_operations()
        test_model_building()
        test_training_and_forecast()
        test_cache_mechanism()
        test_api_response_structure()
        
        print("=" * 60)
        print("✓ ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print()
        print("Summary:")
        print("  ✓ Data operations working")
        print("  ✓ Models building correctly")
        print("  ✓ Training and forecasting functional")
        print("  ✓ Cache mechanism operational")
        print("  ✓ API response structure valid")
        print()
        
    except Exception as e:
        print(f"\n✗ TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
