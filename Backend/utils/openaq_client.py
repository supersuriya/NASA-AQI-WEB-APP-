"""
OpenAQ API client for fetching air quality data.
"""
import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import time

logger = logging.getLogger(__name__)

class OpenAQClient:
    """
    Client for interacting with the OpenAQ API.
    """
    
    def __init__(self, base_url: str = "https://api.openaq.org/v2"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AirSense/1.0 (Air Quality Forecasting App)'
        })
    
    def get_measurements(
        self, 
        city: str, 
        parameters: List[str] = None,
        limit: int = 10000,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch air quality measurements from OpenAQ API.
        
        Args:
            city: City name to fetch data for
            parameters: List of parameters to fetch (PM2.5, O3, NO2)
            limit: Maximum number of records to fetch
            date_from: Start date for data (default: 7 days ago)
            date_to: End date for data (default: now)
        
        Returns:
            List of measurement dictionaries
        """
        if parameters is None:
            parameters = ["PM2.5", "O3", "NO2"]
        
        if date_from is None:
            date_from = datetime.utcnow() - timedelta(days=7)
        if date_to is None:
            date_to = datetime.utcnow()
        
        all_measurements = []
        
        for parameter in parameters:
            try:
                logger.info(f"Fetching {parameter} data for {city}")
                
                # Prepare API parameters
                params = {
                    'city': city,
                    'parameter': parameter,
                    'limit': limit,
                    'date_from': date_from.isoformat(),
                    'date_to': date_to.isoformat(),
                    'format': 'json'
                }
                
                # Make API request
                response = self.session.get(
                    f"{self.base_url}/measurements",
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                
                data = response.json()
                
                if 'results' in data:
                    measurements = data['results']
                    logger.info(f"Fetched {len(measurements)} {parameter} measurements for {city}")
                    
                    # Process and normalize measurements
                    for measurement in measurements:
                        processed = self._process_measurement(measurement, city, parameter)
                        if processed:
                            all_measurements.append(processed)
                
                # Rate limiting - be respectful to the API
                time.sleep(0.1)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching {parameter} data for {city}: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error fetching {parameter} data for {city}: {e}")
                continue
        
        logger.info(f"Total measurements fetched for {city}: {len(all_measurements)}")
        return all_measurements
    
    def _process_measurement(self, measurement: Dict[str, Any], city: str, parameter: str) -> Optional[Dict[str, Any]]:
        """
        Process and normalize a single measurement from OpenAQ API.
        """
        try:
            # Extract relevant fields
            value = measurement.get('value')
            unit = measurement.get('unit')
            date_utc = measurement.get('date', {}).get('utc')
            
            # Validate required fields
            if value is None or unit is None or date_utc is None:
                return None
            
            # Convert value to float
            try:
                value = float(value)
            except (ValueError, TypeError):
                return None
            
            # Parse UTC date
            try:
                date_utc = datetime.fromisoformat(date_utc.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                return None
            
            # Normalize parameter names
            param_mapping = {
                'pm25': 'PM2.5',
                'pm2.5': 'PM2.5',
                'o3': 'O3',
                'no2': 'NO2'
            }
            normalized_param = param_mapping.get(parameter.lower(), parameter.upper())
            
            return {
                'city': city,
                'parameter': normalized_param,
                'value': value,
                'unit': unit,
                'date_utc': date_utc,
                'source': 'openaq',
                'raw_data': measurement  # Store raw data for debugging
            }
            
        except Exception as e:
            logger.error(f"Error processing measurement: {e}")
            return None
    
    def get_available_cities(self, country: str = "US") -> List[str]:
        """
        Get list of available cities in a country.
        """
        try:
            params = {
                'country': country,
                'limit': 1000
            }
            
            response = self.session.get(
                f"{self.base_url}/cities",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            cities = []
            
            if 'results' in data:
                for city_data in data['results']:
                    city_name = city_data.get('city')
                    if city_name:
                        cities.append(city_name)
            
            return sorted(cities)
            
        except Exception as e:
            logger.error(f"Error fetching available cities: {e}")
            return []
    
    def get_parameter_info(self) -> Dict[str, Any]:
        """
        Get information about available parameters.
        """
        try:
            response = self.session.get(f"{self.base_url}/parameters", timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return data
            
        except Exception as e:
            logger.error(f"Error fetching parameter info: {e}")
            return {}
