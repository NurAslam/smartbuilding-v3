#!/usr/bin/env python3
"""
Quick reference for all 6 new forecast endpoints
"""

ENERGY_ENDPOINTS = {
    "daily": {
        "url": "GET /realtime/forecast-energy/daily",
        "description": "24-hour energy consumption forecast (kWh)",
        "example": "curl 'http://localhost:8000/realtime/forecast-energy/daily?hours=72'",
        "params": {
            "model_type": "lstm|rnn (default: lstm)",
            "hours": "24-240 (default: 72)",
            "ref_datetime": "ISO datetime (optional)"
        },
        "response_sample": {
            "metric": "energy_kwh",
            "forecast": [0.732, 0.734, 0.725, ...],  # 24 values
            "forecast_with_timestamps": [
                {"timestamp": "2025-11-27T22:00:00+07:00", "value": 0.732},
                ...
            ]
        }
    },
    "weekly": {
        "url": "GET /realtime/forecast-energy/weekly",
        "description": "7-day energy consumption forecast (daily average)",
        "example": "curl 'http://localhost:8000/realtime/forecast-energy/weekly?days=90'",
        "params": {
            "model_type": "lstm|rnn (default: lstm)",
            "days": "14-90 (default: 90)",
            "ref_date": "ISO date (optional)"
        },
        "response_sample": {
            "metric": "energy_kwh",
            "forecast": [0.85, 0.82, 0.79, ...],  # 7 values (daily average)
            "forecast_with_timestamps": [
                {"timestamp": "2025-11-27", "value": 0.85},
                ...
            ]
        }
    },
    "monthly": {
        "url": "GET /realtime/forecast-energy/monthly",
        "description": "30-day energy consumption forecast (daily average)",
        "example": "curl 'http://localhost:8000/realtime/forecast-energy/monthly?days=365'",
        "params": {
            "model_type": "lstm|rnn (default: lstm)",
            "days": "30-365 (default: 90)",
            "ref_date": "ISO date (optional)"
        },
        "response_sample": {
            "metric": "energy_kwh",
            "forecast": [0.85, 0.82, 0.79, ...],  # 30 values (daily average)
            "forecast_with_timestamps": [
                {"timestamp": "2025-11-27", "value": 0.85},
                ...
            ]
        }
    }
}

COMFORT_ENDPOINTS = {
    "daily": {
        "url": "GET /realtime/forecast-comfort/daily",
        "description": "24-hour thermal comfort forecast (PPV or PPD)",
        "example_ppv": "curl 'http://localhost:8000/realtime/forecast-comfort/daily?target=ppv&hours=72'",
        "example_ppd": "curl 'http://localhost:8000/realtime/forecast-comfort/daily?target=ppd&hours=72'",
        "params": {
            "model_type": "lstm|rnn (default: lstm)",
            "target": "ppv (Predicted Perception Vote) | ppd (% Dissatisfied) [default: ppv]",
            "hours": "24-240 (default: 72)",
            "ref_datetime": "ISO datetime (optional)"
        },
        "ppv_scale": "-3 (Sangat Dingin) to +3 (Sangat Panas)",
        "ppd_scale": "0-100 (% dissatisfied)",
        "response_sample_ppv": {
            "metric": "ppv",
            "forecast": [0.59, 0.61, 0.62, ...],  # 24 values
            "forecast_with_timestamps": [
                {"timestamp": "2025-11-27T22:00:00+07:00", "value": 0.59},
                ...
            ]
        },
        "response_sample_ppd": {
            "metric": "ppd",
            "forecast": [25.5, 26.1, 27.2, ...],  # 24 values (% dissatisfied)
            "forecast_with_timestamps": [
                {"timestamp": "2025-11-27T22:00:00+07:00", "value": 25.5},
                ...
            ]
        }
    },
    "weekly": {
        "url": "GET /realtime/forecast-comfort/weekly",
        "description": "7-day thermal comfort forecast (daily average PPV or PPD)",
        "example_ppv": "curl 'http://localhost:8000/realtime/forecast-comfort/weekly?target=ppv&days=90'",
        "example_ppd": "curl 'http://localhost:8000/realtime/forecast-comfort/weekly?target=ppd&days=90'",
        "params": {
            "model_type": "lstm|rnn (default: lstm)",
            "target": "ppv | ppd (default: ppv)",
            "days": "14-90 (default: 90)",
            "ref_date": "ISO date (optional)"
        },
        "response_sample": {
            "metric": "ppv or ppd",
            "forecast": [0.85, 0.82, 0.79, ...],  # 7 values (daily average)
            "forecast_with_timestamps": [
                {"timestamp": "2025-11-27", "value": 0.85},
                ...
            ]
        }
    },
    "monthly": {
        "url": "GET /realtime/forecast-comfort/monthly",
        "description": "30-day thermal comfort forecast (daily average PPV or PPD)",
        "example_ppv": "curl 'http://localhost:8000/realtime/forecast-comfort/monthly?target=ppv&days=365'",
        "example_ppd": "curl 'http://localhost:8000/realtime/forecast-comfort/monthly?target=ppd&days=365'",
        "params": {
            "model_type": "lstm|rnn (default: lstm)",
            "target": "ppv | ppd (default: ppv)",
            "days": "30-365 (default: 90)",
            "ref_date": "ISO date (optional)"
        },
        "response_sample": {
            "metric": "ppv or ppd",
            "forecast": [0.85, 0.82, 0.79, ...],  # 30 values (daily average)
            "forecast_with_timestamps": [
                {"timestamp": "2025-11-27", "value": 0.85},
                ...
            ]
        }
    }
}


if __name__ == "__main__":
    print("=" * 80)
    print("ENERGY CONSUMPTION FORECAST ENDPOINTS")
    print("=" * 80)
    for granularity, details in ENERGY_ENDPOINTS.items():
        print(f"\n{granularity.upper()}")
        print(f"  URL: {details['url']}")
        print(f"  Description: {details['description']}")
        print(f"  Example: {details['example']}")
        print(f"  Parameters: {details['params']}")

    print("\n" + "=" * 80)
    print("THERMAL COMFORT FORECAST ENDPOINTS")
    print("=" * 80)
    for granularity, details in COMFORT_ENDPOINTS.items():
        print(f"\n{granularity.upper()}")
        print(f"  URL: {details['url']}")
        print(f"  Description: {details['description']}")
        print(f"  Example (PPV): {details['example_ppv']}")
        print(f"  Example (PPD): {details['example_ppd']}")
        print(f"  Parameters: {details['params']}")
        if 'ppv_scale' in details:
            print(f"  PPV Scale: {details['ppv_scale']}")
            print(f"  PPD Scale: {details['ppd_scale']}")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total New Endpoints: 6")
    print(f"  - Energy Forecasts: 3 (daily, weekly, monthly)")
    print(f"  - Comfort Forecasts: 3 (daily, weekly, monthly)")
    print(f"\nData Source: sensor_hourly table")
    print(f"Models: LSTM (default) or RNN")
    print(f"Caching: Yes (auto-update with hash detection)")
    print(f"Performance: 2-5s first request, ~100ms cached")
    print(f"\nDocumentation: FORECAST_ENERGY_COMFORT.md")
    print(f"Implementation Summary: IMPLEMENTATION_ENERGY_COMFORT_FORECAST.md")
