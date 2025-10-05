"""
Test database connection and table creation.
"""
from database import create_tables, init_cities_from_config, get_db, Measurement, Weather
from sqlalchemy.orm import Session

def test_database():
    """Test database operations."""
    print("Testing database connection...")
    
    try:
        # Create tables
        create_tables()
        print("SUCCESS: Database tables created")
        
        # Initialize cities
        init_cities_from_config()
        print("SUCCESS: Cities initialized")
        
        # Test database session
        db = next(get_db())
        print("SUCCESS: Database session created")
        
        # Test queries
        measurements = db.query(Measurement).all()
        weather = db.query(Weather).all()
        print(f"SUCCESS: Queries work - {len(measurements)} measurements, {len(weather)} weather records")
        
        db.close()
        print("SUCCESS: Database test completed")
        
    except Exception as e:
        print(f"ERROR: Database test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_database()
