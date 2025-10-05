"""
Configuration for AirSense application with real NASA credentials.
"""
import os

# NASA Earthdata credentials
NASA_CREDENTIALS = {
    'username': 'Vishwajaikumar',
    'password': 'Og3zf68k2008$'
}

# Geographic configuration
NORTH_AMERICA_BBOX = [-180, 15, -50, 70]  # [west, south, east, north]

# Time configuration
HISTORICAL_DAYS = 365  # 1 year of historical data

# Data sources
DATA_SOURCES = ['tempo', 'pandora', 'tolnet', 'airnow']

# Parameters to fetch
PARAMETERS = ['NO2', 'O3', 'HCHO', 'H2CO', 'PM2.5']

# Output configuration
OUTPUT_FORMAT = 'csv'
CSV_OUTPUT_DIR = 'data/csv_exports'

# Database configuration
DATABASE_URL = 'sqlite:///./airsense.db'

# API configuration
API_HOST = '0.0.0.0'
API_PORT = 8000

# Logging
LOG_LEVEL = 'INFO'
