"""
Demo script showing how to use the AirSense API.
"""
import requests
import json
import time

# API base URL
BASE_URL = "http://localhost:8000"

def test_health():
    """Test the health endpoint."""
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✓ Health check passed")
            print(f"  Response: {response.json()}")
        else:
            print(f"✗ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Health check error: {e}")

def test_ingest_nasa():
    """Test NASA data ingestion."""
    print("\nTesting NASA data ingestion...")
    try:
        response = requests.post(
            f"{BASE_URL}/ingest/nasa",
            params={
                "city": "New York",
                "days_back": 7,
                "parameters": ["NO2", "O3", "HCHO", "PM2.5"],
                "sources": ["tempo", "pandora", "tolnet", "airnow"]
            }
        )
        if response.status_code == 200:
            print("✓ NASA data ingestion successful")
            print(f"  Response: {response.json()}")
        else:
            print(f"✗ NASA data ingestion failed: {response.status_code}")
            print(f"  Error: {response.text}")
    except Exception as e:
        print(f"✗ NASA data ingestion error: {e}")

def test_measurements():
    """Test getting measurements."""
    print("\nTesting measurements endpoint...")
    try:
        response = requests.get(
            f"{BASE_URL}/measurements",
            params={"city": "New York", "limit": 10}
        )
        if response.status_code == 200:
            measurements = response.json()
            print(f"✓ Retrieved {len(measurements)} measurements")
            if measurements:
                print(f"  Sample: {measurements[0]}")
        else:
            print(f"✗ Measurements retrieval failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Measurements error: {e}")

def test_forecast():
    """Test forecasting."""
    print("\nTesting forecast endpoint...")
    try:
        forecast_data = {
            "city": "New York",
            "parameter": "PM2.5",
            "hours_ahead": 24
        }
        response = requests.post(
            f"{BASE_URL}/forecast",
            json=forecast_data
        )
        if response.status_code == 200:
            forecasts = response.json()
            print(f"✓ Generated {len(forecasts)} forecast points")
            if forecasts:
                print(f"  Sample forecast: {forecasts[0]}")
        else:
            print(f"✗ Forecast failed: {response.status_code}")
            print(f"  Error: {response.text}")
    except Exception as e:
        print(f"✗ Forecast error: {e}")

def test_train_model():
    """Test model training."""
    print("\nTesting model training...")
    try:
        response = requests.post(
            f"{BASE_URL}/train-model",
            params={"city": "New York", "parameter": "PM2.5"}
        )
        if response.status_code == 200:
            print("✓ Model training successful")
            print(f"  Response: {response.json()}")
        else:
            print(f"✗ Model training failed: {response.status_code}")
            print(f"  Error: {response.text}")
    except Exception as e:
        print(f"✗ Model training error: {e}")

def main():
    """Run all demo tests."""
    print("🚀 AirSense API Demo")
    print("=" * 50)
    
    # Wait a moment for the server to be ready
    print("Waiting for server to be ready...")
    time.sleep(2)
    
    # Run tests
    test_health()
    test_ingest_nasa()
    test_measurements()
    test_forecast()
    test_train_model()
    
    print("\n" + "=" * 50)
    print("Demo completed!")

if __name__ == "__main__":
    main()
