#!/usr/bin/env python3
import requests
import json

# Test daily energy forecast
print("=" * 70)
print("Testing Daily Energy Forecast")
print("=" * 70)
resp = requests.get('http://localhost:8000/realtime/forecast-energy/daily')
print(f'Status: {resp.status_code}')
if resp.status_code == 200:
    data = resp.json()
    print(json.dumps({
        "metric": data.get("metric"),
        "granularity": data.get("granularity"),
        "forecast_samples": data.get("forecast")[:3],
        "model_used": data.get("model_used"),
        "training_datapoints": data.get("training_datapoints"),
    }, indent=2))

# Test daily PPV comfort forecast
print("\n" + "=" * 70)
print("Testing Daily PPV Comfort Forecast")
print("=" * 70)
resp = requests.get('http://localhost:8000/realtime/forecast-comfort/daily?target=ppv')
print(f'Status: {resp.status_code}')
if resp.status_code == 200:
    data = resp.json()
    print(json.dumps({
        "metric": data.get("metric"),
        "granularity": data.get("granularity"),
        "forecast_samples": data.get("forecast")[:3],
        "model_used": data.get("model_used"),
        "training_datapoints": data.get("training_datapoints"),
    }, indent=2))

# Test daily PPD comfort forecast
print("\n" + "=" * 70)
print("Testing Daily PPD Comfort Forecast")
print("=" * 70)
resp = requests.get('http://localhost:8000/realtime/forecast-comfort/daily?target=ppd')
print(f'Status: {resp.status_code}')
if resp.status_code == 200:
    data = resp.json()
    print(json.dumps({
        "metric": data.get("metric"),
        "granularity": data.get("granularity"),
        "forecast_samples": data.get("forecast")[:3],
        "model_used": data.get("model_used"),
        "training_datapoints": data.get("training_datapoints"),
    }, indent=2))
