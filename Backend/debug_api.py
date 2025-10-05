"""
Debug API endpoints to find the issue.
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_normalized_data():
    """Test normalized data endpoint with detailed error info."""
    print("Testing normalized data endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/data/normalized?days_back=1")
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print("SUCCESS: Normalized data retrieved")
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"ERROR: Status {response.status_code}")
            print(f"Error Response: {response.text}")
            
    except Exception as e:
        print(f"ERROR: Exception occurred: {e}")

def test_data_stats():
    """Test data stats endpoint with detailed error info."""
    print("\nTesting data stats endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/data/stats")
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print("SUCCESS: Data stats retrieved")
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"ERROR: Status {response.status_code}")
            print(f"Error Response: {response.text}")
            
    except Exception as e:
        print(f"ERROR: Exception occurred: {e}")

if __name__ == "__main__":
    test_normalized_data()
    test_data_stats()
