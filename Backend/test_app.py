"""
Simple test script to verify AirSense application structure.
"""
import sys
import os

def test_imports():
    """Test that all modules can be imported."""
    try:
        # Test database module
        from database import get_db, create_tables
        print("OK: Database module imports successfully")
        
        # Test models
        from models import Measurement, Forecast
        print("OK: Models import successfully")
        
        # Test schemas
        from schemas import ForecastRequest, ForecastResponse, HealthResponse
        print("OK: Schemas import successfully")
        
        # Test ML model
        from ml_model import AirQualityForecaster
        print("OK: ML model imports successfully")
        
        # Test utils
        from utils.openaq_client import OpenAQClient
        from utils.tempo_client import TEMPOClient
        from utils.data_processor import DataProcessor
        print("OK: Utils modules import successfully")
        
        print("\nSUCCESS: All modules import successfully!")
        return True
        
    except ImportError as e:
        print(f"ERROR: Import error: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return False

def test_database_creation():
    """Test database table creation."""
    try:
        from database import create_tables
        create_tables()
        print("OK: Database tables created successfully")
        return True
    except Exception as e:
        print(f"ERROR: Database creation error: {e}")
        return False

def test_schema_validation():
    """Test Pydantic schema validation."""
    try:
        from schemas import ForecastRequest, HealthResponse
        from datetime import datetime
        
        # Test forecast request
        forecast_req = ForecastRequest(
            city="New York",
            parameter="PM2.5",
            hours_ahead=24
        )
        print("OK: ForecastRequest validation works")
        
        # Test health response
        health_resp = HealthResponse()
        print("OK: HealthResponse validation works")
        
        return True
    except Exception as e:
        print(f"ERROR: Schema validation error: {e}")
        return False

if __name__ == "__main__":
    print("Testing AirSense application structure...\n")
    
    tests = [
        ("Import Tests", test_imports),
        ("Database Tests", test_database_creation),
        ("Schema Tests", test_schema_validation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        if test_func():
            passed += 1
        else:
            print(f"ERROR: {test_name} failed")
    
    print(f"\n--- Results ---")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("SUCCESS: All tests passed! The application structure is correct.")
        sys.exit(0)
    else:
        print("ERROR: Some tests failed. Please check the errors above.")
        sys.exit(1)
