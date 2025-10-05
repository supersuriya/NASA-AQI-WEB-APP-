"""
Test script to demonstrate real NASA TEMPO data access.
"""
import os
import sys
from datetime import datetime, timedelta

# Add current directory to path
sys.path.append('.')

def test_nasa_authentication():
    """Test NASA Earthdata authentication."""
    print("Testing NASA Earthdata authentication...")
    
    try:
        from utils.nasa_data_client import NASADataClient
        client = NASADataClient()
        print("SUCCESS: Successfully authenticated with NASA Earthdata!")
        return client
    except Exception as e:
        print(f"ERROR: Authentication failed: {e}")
        return None

def test_tempo_data_search(client):
    """Test TEMPO data search for North America."""
    print("\nTesting TEMPO data search for North America...")
    
    try:
        # Search for TEMPO data (smaller time range for testing)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)  # Last 7 days for testing
        
        print(f"Searching for TEMPO data from {start_date} to {end_date}")
        
        # This will search for real TEMPO data
        nasa_data = client.get_tempo_data_north_america(
            days_back=7,  # 7 days for testing
            parameters=["NO2", "O3", "HCHO"]
        )
        
        measurements = nasa_data.get('measurements', [])
        csv_file_path = nasa_data.get('csv_file_path')
        
        print(f"SUCCESS: Found {len(measurements)} TEMPO measurements")
        print(f"CSV file created: {csv_file_path}")
        
        if measurements:
            print("\nSample measurements:")
            for i, measurement in enumerate(measurements[:3]):
                print(f"  {i+1}. {measurement['city']} - {measurement['parameter']}: {measurement['value']} {measurement['unit']}")
        
        return nasa_data
        
    except Exception as e:
        print(f"ERROR: Error fetching TEMPO data: {e}")
        return None

def test_database_integration():
    """Test database integration."""
    print("\nTesting database integration...")
    
    try:
        from database import create_tables, get_db
        from models import Measurement
        
        # Create tables
        create_tables()
        print("SUCCESS: Database tables created")
        
        # Test database session
        db = next(get_db())
        print("SUCCESS: Database session established")
        
        # Count existing measurements
        count = db.query(Measurement).count()
        print(f"Database contains {count} measurements")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Database error: {e}")
        return False

def main():
    """Main test function."""
    print("AirSense NASA Data Test")
    print("=" * 50)
    
    # Test 1: NASA Authentication
    client = test_nasa_authentication()
    if not client:
        print("ERROR: Cannot proceed without NASA authentication")
        return
    
    # Test 2: Database Integration
    if not test_database_integration():
        print("ERROR: Database test failed")
        return
    
    # Test 3: TEMPO Data Search
    nasa_data = test_tempo_data_search(client)
    if not nasa_data:
        print("ERROR: TEMPO data test failed")
        return
    
    print("\n" + "=" * 50)
    print("SUCCESS: All tests passed! Your NASA data integration is working!")
    print("\nNext steps:")
    print("1. Run: python main.py")
    print("2. Visit: http://localhost:8000")
    print("3. Test endpoints:")
    print("   - GET /health")
    print("   - POST /ingest/nasa")
    print("   - POST /forecast")
    print("   - GET /export/csv")

if __name__ == "__main__":
    main()
