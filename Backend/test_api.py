"""
Test script for the Air Quality Data Ingestion API.
"""
import requests
import json
import time
from datetime import datetime

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

def test_root():
    """Test the root endpoint."""
    print("\nTesting root endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("SUCCESS: Root endpoint working")
            data = response.json()
            print(f"API: {data['message']}")
            print(f"Version: {data['version']}")
        else:
            print(f"ERROR: Root endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"ERROR: Root endpoint error: {e}")

def test_cities():
    """Test city configuration endpoints."""
    print("\nTesting city configuration...")
    try:
        # Get existing cities
        response = requests.get(f"{BASE_URL}/config/cities")
        if response.status_code == 200:
            cities = response.json()
            print(f"SUCCESS: Found {len(cities)} configured cities")
            for city in cities[:3]:  # Show first 3
                print(f"  - {city['name']}: ({city['latitude']}, {city['longitude']})")
        else:
            print(f"ERROR: Failed to get cities: {response.status_code}")
    except Exception as e:
        print(f"ERROR: City configuration error: {e}")

def test_data_ingestion():
    """Test data ingestion endpoint."""
    print("\nTesting data ingestion...")
    try:
        # Test with 1 day of data for faster testing
        response = requests.get(f"{BASE_URL}/ingest/data?days_back=1")
        if response.status_code == 200:
            result = response.json()
            print("SUCCESS: Data ingestion completed")
            print(f"Total records: {result['total_records']}")
            print(f"Success: {result['success']}")
            print(f"Message: {result['message']}")
            
            # Show results by source
            for source, data in result['results'].items():
                print(f"  {source}: {data['records']} records, success: {data['success']}")
        else:
            print(f"ERROR: Data ingestion failed: {response.status_code}")
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"ERROR: Data ingestion error: {e}")

def test_data_preview():
    """Test data preview endpoint."""
    print("\nTesting data preview...")
    try:
        response = requests.get(f"{BASE_URL}/data/preview?limit=5")
        if response.status_code == 200:
            data = response.json()
            print("SUCCESS: Data preview retrieved")
            print(f"Measurements: {data['total_measurements']}")
            print(f"Weather: {data['total_weather']}")
            
            if data['measurements']:
                print("Sample measurement:")
                m = data['measurements'][0]
                print(f"  {m['city']} - {m['parameter']}: {m['value']} {m['unit']} ({m['source']})")
            
            if data['weather']:
                print("Sample weather:")
                w = data['weather'][0]
                print(f"  {w['city']} - Temp: {w['temperature']}°C, Humidity: {w['humidity']}%")
        else:
            print(f"ERROR: Data preview failed: {response.status_code}")
    except Exception as e:
        print(f"ERROR: Data preview error: {e}")

def test_normalized_data():
    """Test normalized data endpoint."""
    print("\nTesting normalized data...")
    try:
        response = requests.get(f"{BASE_URL}/data/normalized?days_back=1")
        if response.status_code == 200:
            data = response.json()
            print("SUCCESS: Normalized data retrieved")
            print(f"Success: {data['success']}")
            print(f"Total records: {data['total_records']}")
            print(f"Cities: {data['cities']}")
            
            if data['data']:
                print("Sample normalized data:")
                for city, timestamps in list(data['data'].items())[:1]:  # Show first city
                    print(f"  City: {city}")
                    for timestamp, record in list(timestamps.items())[:1]:  # Show first timestamp
                        print(f"    Time: {timestamp}")
                        print(f"    Measurements: {record.get('measurements', {})}")
                        print(f"    Weather: {record.get('weather', {})}")
        else:
            print(f"ERROR: Normalized data failed: {response.status_code}")
    except Exception as e:
        print(f"ERROR: Normalized data error: {e}")

def test_data_stats():
    """Test data statistics endpoint."""
    print("\nTesting data statistics...")
    try:
        response = requests.get(f"{BASE_URL}/data/stats")
        if response.status_code == 200:
            stats = response.json()
            print("SUCCESS: Data statistics retrieved")
            print(f"Total measurements: {stats['total_measurements']}")
            print(f"Total weather: {stats['total_weather']}")
            
            print("Measurement sources:")
            for source in stats['measurement_sources']:
                print(f"  {source['source']}: {source['count']} records")
            
            print("Weather sources:")
            for source in stats['weather_sources']:
                print(f"  {source['source']}: {source['count']} records")
        else:
            print(f"ERROR: Data stats failed: {response.status_code}")
    except Exception as e:
        print(f"ERROR: Data stats error: {e}")

def main():
    """Run all API tests."""
    print("Air Quality Data Ingestion API Test")
    print("=" * 50)
    
    # Wait a moment for the server to be ready
    print("Waiting for server to be ready...")
    time.sleep(2)
    
    # Run tests
    test_health()
    test_root()
    test_cities()
    test_data_ingestion()
    test_data_preview()
    test_normalized_data()
    test_data_stats()
    
    print("\n" + "=" * 50)
    print("API testing completed!")
    print("\nTo start the server, run: python main.py")

if __name__ == "__main__":
    main()
