"""
Startup script for AirSense application.
"""
import os
import sys
import subprocess
from pathlib import Path

def check_environment():
    """Check if required environment variables are set."""
    required_vars = ['EARTHDATA_USERNAME', 'EARTHDATA_PASSWORD']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables or create a .env file from env.example")
        return False
    
    print("✅ Environment variables check passed")
    return True

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import fastapi
        import sqlalchemy
        import pandas
        import numpy
        import sklearn
        print("✅ Core dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("Please install dependencies with: pip install -r requirements.txt")
        return False

def create_directories():
    """Create necessary directories."""
    directories = ['data', 'data/tempo', 'models', 'logs']
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def main():
    """Main startup function."""
    print("🚀 Starting AirSense application...\n")
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Start the application
    print("\n🌟 Starting FastAPI server...")
    try:
        import uvicorn
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down AirSense application...")
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
