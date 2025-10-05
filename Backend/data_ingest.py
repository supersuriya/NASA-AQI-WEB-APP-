"""
Data ingestion module for fetching data from multiple APIs.
Supports NASA TOLNet, OpenAQ, and weather APIs.
"""
import os
import json
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging
import time
import earthaccess
from sqlalchemy.orm import Session
from models import Measurement
from database import Base, engine

# Create Weather model if it doesn't exist
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func

class Weather(Base):
    __tablename__ = "weather"
    id = Column(Integer, primary_key=True, index=True)
    city = Column(String(100), nullable=False, index=True)
    temperature = Column(Float)
    humidity = Column(Float)
    wind_speed = Column(Float)
    wind_direction = Column(Float)
    precipitation = Column(Float)
    pressure = Column(Float)
    datetime_utc = Column(DateTime, nullable=False, index=True)
    source = Column(String(20), nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    raw_data = Column(String)
    created_at = Column(DateTime, default=func.now())

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataIngestionManager:
    """
    Main class for managing data ingestion from multiple APIs.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.config = self._load_config()
        self.earthdata_username = os.getenv('EARTHDATA_USERNAME')
        self.earthdata_password = os.getenv('EARTHDATA_PASSWORD')
        
        # Initialize NASA Earthdata authentication
        self._authenticate_earthdata()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.json."""
        try:
            with open('config.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error("config.json not found. Using default configuration.")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration if config.json is not available."""
        return {
            "cities": [
                {"name": "New York", "latitude": 40.7128, "longitude": -74.0060, "timezone": "America/New_York"},
                {"name": "Los Angeles", "latitude": 34.0522, "longitude": -118.2437, "timezone": "America/Los_Angeles"}
            ],
            "ingestion_settings": {"days_back": 7, "update_frequency_hours": 6, "retry_attempts": 3, "timeout_seconds": 30},
            "data_sources": {
                "tolnet": {"enabled": True, "base_url": "https://tolnet.larc.nasa.gov/api/"},
                "openaq": {"enabled": True, "base_url": "https://api.openaq.org/v2/"},
                "weather": {"enabled": True, "sources": ["daymet", "merra2"]}
            }
        }
    
    def _authenticate_earthdata(self):
        """Authenticate with NASA Earthdata."""
        try:
            if self.earthdata_username and self.earthdata_password:
                os.environ['EARTHDATA_USERNAME'] = self.earthdata_username
                os.environ['EARTHDATA_PASSWORD'] = self.earthdata_password
                earthaccess.login()
                logger.info("Successfully authenticated with NASA Earthdata")
            else:
                logger.warning("NASA Earthdata credentials not provided")
        except Exception as e:
            logger.error(f"Failed to authenticate with NASA Earthdata: {e}")
    
    def ingest_all_data(self, days_back: int = None) -> Dict[str, Any]:
        """
        Ingest data from all enabled sources.
        
        Args:
            days_back: Number of days to look back for data
            
        Returns:
            Dictionary with ingestion results
        """
        if days_back is None:
            days_back = self.config['ingestion_settings']['days_back']
        
        logger.info(f"Starting data ingestion for last {days_back} days")
        
        results = {
            'tolnet': {'success': False, 'records': 0, 'error': None},
            'openaq': {'success': False, 'records': 0, 'error': None},
            'weather': {'success': False, 'records': 0, 'error': None}
        }
        
        # Ingest TOLNet data
        if self.config['data_sources']['tolnet']['enabled']:
            try:
                tolnet_data = self.ingest_tolnet_data(days_back)
                results['tolnet'] = tolnet_data
            except Exception as e:
                logger.error(f"TOLNet ingestion failed: {e}")
                results['tolnet']['error'] = str(e)
        
        # Ingest OpenAQ data
        if self.config['data_sources']['openaq']['enabled']:
            try:
                openaq_data = self.ingest_openaq_data(days_back)
                results['openaq'] = openaq_data
            except Exception as e:
                logger.error(f"OpenAQ ingestion failed: {e}")
                results['openaq']['error'] = str(e)
        
        # Ingest weather data
        if self.config['data_sources']['weather']['enabled']:
            try:
                weather_data = self.ingest_weather_data(days_back)
                results['weather'] = weather_data
            except Exception as e:
                logger.error(f"Weather ingestion failed: {e}")
                results['weather']['error'] = str(e)
        
        # Calculate total records
        total_records = sum(result['records'] for result in results.values())
        
        logger.info(f"Data ingestion completed. Total records: {total_records}")
        
        return {
            'total_records': total_records,
            'results': results,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def ingest_tolnet_data(self, days_back: int) -> Dict[str, Any]:
        """
        Ingest data from NASA TOLNet API.
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            Dictionary with ingestion results
        """
        logger.info("Ingesting TOLNet data...")
        
        base_url = self.config['data_sources']['tolnet']['base_url']
        records_processed = 0
        
        try:
            # Get list of available data
            data_list_url = f"{base_url}data/"
            response = requests.get(data_list_url, timeout=30)
            response.raise_for_status()
            
            data_list = response.json()
            logger.info(f"Found {len(data_list)} TOLNet datasets")
            
            # Process each dataset
            for dataset in data_list[:10]:  # Limit to first 10 for testing
                try:
                    dataset_id = dataset.get('id')
                    if not dataset_id:
                        continue
                    
                    # Get data for this dataset
                    data_url = f"{base_url}data/json_for_graph/{dataset_id}"
                    data_response = requests.get(data_url, timeout=30)
                    data_response.raise_for_status()
                    
                    data = data_response.json()
                    
                    # Process O3 data
                    if 'O3_Number_Density' in data and 'timestamps' in data:
                        o3_values = data['O3_Number_Density']
                        timestamps = data['timestamps']
                        
                        # Find closest city
                        city = self._find_closest_city(dataset.get('latitude', 0), dataset.get('longitude', 0))
                        
                        # Store measurements
                        for i, (value, timestamp) in enumerate(zip(o3_values, timestamps)):
                            if value is not None and timestamp:
                                measurement = Measurement(
                                    city=city,
                                    parameter='O3',
                                    value=float(value),
                                    unit='molecules/cm³',
                                    datetime_utc=datetime.fromisoformat(timestamp.replace('Z', '+00:00')),
                                    source='tolnet',
                                    latitude=dataset.get('latitude'),
                                    longitude=dataset.get('longitude'),
                                    raw_data=json.dumps(data)
                                )
                                self.db.add(measurement)
                                records_processed += 1
                    
                    # Small delay to avoid overwhelming the API
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error processing TOLNet dataset {dataset_id}: {e}")
                    continue
            
            self.db.commit()
            logger.info(f"TOLNet ingestion completed. Records processed: {records_processed}")
            
            return {
                'success': True,
                'records': records_processed,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"TOLNet API error: {e}")
            self.db.rollback()
            return {
                'success': False,
                'records': 0,
                'error': str(e)
            }
    
    def ingest_openaq_data(self, days_back: int) -> Dict[str, Any]:
        """
        Ingest data from OpenAQ API.
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            Dictionary with ingestion results
        """
        logger.info("Ingesting OpenAQ data...")
        
        base_url = self.config['data_sources']['openaq']['base_url']
        records_processed = 0
        
        try:
            # Get cities from config
            cities = [city['name'] for city in self.config['cities']]
            
            for city in cities:
                try:
                    # Calculate date range
                    end_date = datetime.utcnow()
                    start_date = end_date - timedelta(days=days_back)
                    
                    # Fetch measurements for this city
                    params = {
                        'city': city,
                        'date_from': start_date.isoformat(),
                        'date_to': end_date.isoformat(),
                        'limit': 1000
                    }
                    
                    response = requests.get(f"{base_url}measurements", params=params, timeout=30)
                    response.raise_for_status()
                    
                    data = response.json()
                    measurements = data.get('results', [])
                    
                    logger.info(f"Found {len(measurements)} OpenAQ measurements for {city}")
                    
                    # Process measurements
                    for measurement in measurements:
                        try:
                            # Extract data
                            value = measurement.get('value')
                            parameter = measurement.get('parameter')
                            unit = measurement.get('unit')
                            date_utc = measurement.get('date', {}).get('utc')
                            location = measurement.get('location', {})
                            
                            if value is not None and parameter and unit and date_utc:
                                # Normalize parameter names
                                param_mapping = {
                                    'pm25': 'PM2.5',
                                    'pm2.5': 'PM2.5',
                                    'pm10': 'PM10',
                                    'no2': 'NO2',
                                    'o3': 'O3',
                                    'so2': 'SO2',
                                    'co': 'CO'
                                }
                                normalized_param = param_mapping.get(parameter.lower(), parameter.upper())
                                
                                # Convert units to µg/m³
                                normalized_value, normalized_unit = self._normalize_units(value, unit, normalized_param)
                                
                                # Store measurement
                                db_measurement = Measurement(
                                    city=city,
                                    parameter=normalized_param,
                                    value=normalized_value,
                                    unit=normalized_unit,
                                    datetime_utc=datetime.fromisoformat(date_utc.replace('Z', '+00:00')),
                                    source='openaq',
                                    latitude=location.get('latitude'),
                                    longitude=location.get('longitude'),
                                    raw_data=json.dumps(measurement)
                                )
                                self.db.add(db_measurement)
                                records_processed += 1
                                
                        except Exception as e:
                            logger.error(f"Error processing OpenAQ measurement: {e}")
                            continue
                    
                    # Small delay between cities
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error fetching OpenAQ data for {city}: {e}")
                    continue
            
            self.db.commit()
            logger.info(f"OpenAQ ingestion completed. Records processed: {records_processed}")
            
            return {
                'success': True,
                'records': records_processed,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"OpenAQ API error: {e}")
            self.db.rollback()
            return {
                'success': False,
                'records': 0,
                'error': str(e)
            }
    
    def ingest_weather_data(self, days_back: int) -> Dict[str, Any]:
        """
        Ingest weather data from NASA Daymet and MERRA-2.
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            Dictionary with ingestion results
        """
        logger.info("Ingesting weather data...")
        
        records_processed = 0
        
        try:
            # Get cities from config
            cities = self.config['cities']
            
            for city_data in cities:
                try:
                    city_name = city_data['name']
                    lat = city_data['latitude']
                    lon = city_data['longitude']
                    
                    # Calculate date range
                    end_date = datetime.utcnow()
                    start_date = end_date - timedelta(days=days_back)
                    
                    # Fetch Daymet data
                    daymet_data = self._fetch_daymet_data(lat, lon, start_date, end_date)
                    
                    # Process Daymet data
                    for record in daymet_data:
                        weather = Weather(
                            city=city_name,
                            temperature=record.get('temperature'),
                            humidity=record.get('humidity'),
                            wind_speed=record.get('wind_speed'),
                            wind_direction=record.get('wind_direction'),
                            precipitation=record.get('precipitation'),
                            pressure=record.get('pressure'),
                            datetime_utc=record['datetime_utc'],
                            source='daymet',
                            latitude=lat,
                            longitude=lon,
                            raw_data=json.dumps(record)
                        )
                        self.db.add(weather)
                        records_processed += 1
                    
                    # Small delay between cities
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error fetching weather data for {city_data['name']}: {e}")
                    continue
            
            self.db.commit()
            logger.info(f"Weather ingestion completed. Records processed: {records_processed}")
            
            return {
                'success': True,
                'records': records_processed,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Weather data error: {e}")
            self.db.rollback()
            return {
                'success': False,
                'records': 0,
                'error': str(e)
            }
    
    def _fetch_daymet_data(self, lat: float, lon: float, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Fetch weather data from NASA Daymet.
        
        Args:
            lat: Latitude
            lon: Longitude
            start_date: Start date
            end_date: End date
            
        Returns:
            List of weather records
        """
        try:
            # This is a simplified implementation
            # In practice, you would use the Daymet API or download NetCDF files
            
            weather_data = []
            current_date = start_date
            
            while current_date <= end_date:
                # Simulate weather data (replace with actual API call)
                weather_record = {
                    'datetime_utc': current_date,
                    'temperature': np.random.normal(20, 10),  # Simulated temperature
                    'humidity': np.random.uniform(30, 90),    # Simulated humidity
                    'wind_speed': np.random.uniform(0, 15),   # Simulated wind speed
                    'wind_direction': np.random.uniform(0, 360),  # Simulated wind direction
                    'precipitation': np.random.exponential(2),    # Simulated precipitation
                    'pressure': np.random.normal(1013, 20)    # Simulated pressure
                }
                weather_data.append(weather_record)
                current_date += timedelta(days=1)
            
            return weather_data
            
        except Exception as e:
            logger.error(f"Error fetching Daymet data: {e}")
            return []
    
    def _find_closest_city(self, lat: float, lon: float) -> str:
        """
        Find the closest city to given coordinates.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            City name
        """
        cities = self.config['cities']
        min_distance = float('inf')
        closest_city = cities[0]['name']
        
        for city in cities:
            distance = ((lat - city['latitude']) ** 2 + (lon - city['longitude']) ** 2) ** 0.5
            if distance < min_distance:
                min_distance = distance
                closest_city = city['name']
        
        return closest_city
    
    def _normalize_units(self, value: float, unit: str, parameter: str) -> Tuple[float, str]:
        """
        Normalize units to standard format.
        
        Args:
            value: Measurement value
            unit: Original unit
            parameter: Parameter name
            
        Returns:
            Tuple of (normalized_value, normalized_unit)
        """
        unit = unit.lower().strip()
        
        # Unit conversion factors to µg/m³
        conversion_factors = {
            'µg/m³': 1.0,
            'ug/m3': 1.0,
            'mg/m³': 1000.0,
            'mg/m3': 1000.0,
            'ppm': self._ppm_to_ugm3(parameter),
            'ppb': self._ppb_to_ugm3(parameter)
        }
        
        factor = conversion_factors.get(unit, 1.0)
        normalized_value = value * factor
        normalized_unit = 'µg/m³'
        
        return normalized_value, normalized_unit
    
    def _ppm_to_ugm3(self, parameter: str) -> float:
        """Convert ppm to µg/m³ based on parameter."""
        # Simplified conversion (would need molecular weights for accuracy)
        conversions = {
            'NO2': 1880,  # Approximate conversion factor
            'O3': 2000,
            'SO2': 2620,
            'CO': 1150
        }
        return conversions.get(parameter, 1000)
    
    def _ppb_to_ugm3(self, parameter: str) -> float:
        """Convert ppb to µg/m³ based on parameter."""
        return self._ppm_to_ugm3(parameter) / 1000
    
    def get_normalized_data(self, city: str = None, days_back: int = 7) -> Dict[str, Any]:
        """
        Get normalized data ready for ML model input.
        
        Args:
            city: Specific city (optional)
            days_back: Number of days to look back
            
        Returns:
            Dictionary with normalized data
        """
        try:
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)
            
            # Query measurements
            measurements_query = self.db.query(Measurement).filter(
                Measurement.datetime_utc >= start_date,
                Measurement.datetime_utc <= end_date
            )
            
            if city:
                measurements_query = measurements_query.filter(Measurement.city == city)
            
            measurements = measurements_query.all()
            
            # Query weather data
            weather_query = self.db.query(Weather).filter(
                Weather.datetime_utc >= start_date,
                Weather.datetime_utc <= end_date
            )
            
            if city:
                weather_query = weather_query.filter(Weather.city == city)
            
            weather_data = weather_query.all()
            
            # Group data by city and timestamp
            normalized_data = {}
            
            for measurement in measurements:
                city_name = measurement.city
                timestamp = measurement.datetime_utc.isoformat()
                
                if city_name not in normalized_data:
                    normalized_data[city_name] = {}
                
                if timestamp not in normalized_data[city_name]:
                    normalized_data[city_name][timestamp] = {
                        'city': city_name,
                        'datetime_utc': timestamp,
                        'measurements': {},
                        'weather': {}
                    }
                
                normalized_data[city_name][timestamp]['measurements'][measurement.parameter] = {
                    'value': measurement.value,
                    'unit': measurement.unit,
                    'source': measurement.source
                }
            
            # Add weather data
            for weather in weather_data:
                city_name = weather.city
                timestamp = weather.datetime_utc.isoformat()
                
                if city_name in normalized_data and timestamp in normalized_data[city_name]:
                    normalized_data[city_name][timestamp]['weather'] = {
                        'temperature': weather.temperature,
                        'humidity': weather.humidity,
                        'wind_speed': weather.wind_speed,
                        'wind_direction': weather.wind_direction,
                        'precipitation': weather.precipitation,
                        'pressure': weather.pressure,
                        'source': weather.source
                    }
            
            return {
                'success': True,
                'data': normalized_data,
                'total_records': len(measurements) + len(weather_data),
                'cities': list(normalized_data.keys())
            }
            
        except Exception as e:
            logger.error(f"Error getting normalized data: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': {},
                'total_records': 0,
                'cities': []
            }
