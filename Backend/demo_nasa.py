"""
Demo script for AirSense NASA data application.
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
            print("SUCCESS: Health check passed")
            print(f"Response: {response.json()}")
        else:
            print(f"ERROR: Health check failed: {response.status_code}")
    except Exception as e:
        print(f"ERROR: Health check error: {e}")

def test_ingest_nasa():
    """Test NASA data ingestion."""
    print("\nTesting NASA TEMPO data ingestion...")
    try:
        response = requests.post(
            f"{BASE_URL}/ingest/nasa",
            params={
                "days_back": 7,  # 7 days for testing
                "parameters": ["NO2", "O3", "HCHO"]
            }
        )
        if response.status_code == 200:
            print("SUCCESS: NASA data ingestion successful")
            result = response.json()
            print(f"Records processed: {result.get('records_processed', 0)}")
            print(f"CSV file: {result.get('csv_file_path', 'None')}")
        else:
            print(f"ERROR: NASA data ingestion failed: {response.status_code}")
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"ERROR: NASA data ingestion error: {e}")

def test_measurements():
    """Test getting measurements."""
    print("\nTesting measurements endpoint...")
    try:
        response = requests.get(
            f"{BASE_URL}/measurements",
            params={"limit": 10}
        )
        if response.status_code == 200:
            measurements = response.json()
            print(f"SUCCESS: Retrieved {len(measurements)} measurements")
            if measurements:
                print("Sample measurement:")
                print(f"  City: {measurements[0].get('city')}")
                print(f"  Parameter: {measurements[0].get('parameter')}")
                print(f"  Value: {measurements[0].get('value')}")
                print(f"  Date: {measurements[0].get('date_utc')}")
        else:
            print(f"ERROR: Measurements retrieval failed: {response.status_code}")
    except Exception as e:
        print(f"ERROR: Measurements error: {e}")

def test_forecast():
    """Test forecasting."""
    print("\nTesting forecast endpoint...")
    try:
        forecast_data = {
            "city": "New York",
            "parameter": "NO2",
            "hours_ahead": 24
        }
        response = requests.post(
            f"{BASE_URL}/forecast",
            json=forecast_data
        )
        if response.status_code == 200:
            forecasts = response.json()
            print(f"SUCCESS: Generated {len(forecasts)} forecast points")
            if forecasts:
                print("Sample forecast:")
                print(f"  City: {forecasts[0].get('city')}")
                print(f"  Parameter: {forecasts[0].get('parameter')}")
                print(f"  Predicted Value: {forecasts[0].get('predicted_value')}")
                print(f"  AQI: {forecasts[0].get('aqi_value')}")
                print(f"  AQI Category: {forecasts[0].get('aqi_category')}")
        else:
            print(f"ERROR: Forecast failed: {response.status_code}")
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"ERROR: Forecast error: {e}")

def test_csv_export():
    """Test CSV export."""
    print("\nTesting CSV export...")
    try:
        export_data = {
            "city": "New York",
            "parameter": "NO2"
        }
        response = requests.post(
            f"{BASE_URL}/export/csv",
            json=export_data
        )
        if response.status_code == 200:
            result = response.json()
            print("SUCCESS: CSV export successful")
            print(f"Records exported: {result.get('records_exported', 0)}")
            print(f"File size: {result.get('file_size_mb', 0)} MB")
            print(f"File path: {result.get('csv_file_path', 'None')}")
        else:
            print(f"ERROR: CSV export failed: {response.status_code}")
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"ERROR: CSV export error: {e}")

def main():
    """Run all demo tests."""
    print("AirSense NASA Data Demo")
    print("=" * 50)
    
    # Wait a moment for the server to be ready
    print("Waiting for server to be ready...")
    time.sleep(2)
    
    # Run tests
    test_health()
    test_ingest_nasa()
    test_measurements()
    test_forecast()
    test_csv_export()
    
    print("\n" + "=" * 50)
    print("Demo completed!")
    print("\nTo start the server, run: python main.py")

if __name__ == "__main__":
    main()
