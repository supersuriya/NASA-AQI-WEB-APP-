"""
NASA Data Client for accessing multiple NASA air quality data sources.
Integrates TEMPO, Pandora, TOLNet, and AirNow data.
"""
import os
import logging
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import earthaccess
import xarray as xr

logger = logging.getLogger(__name__)

class NASADataClient:
    """
    Unified client for accessing NASA air quality data sources.
    """
    
    def __init__(self, username: str = None, password: str = None):
        """
        Initialize NASA data client with Earthdata credentials.
        """
        self.username = username or os.getenv('EARTHDATA_USERNAME')
        self.password = password or os.getenv('EARTHDATA_PASSWORD')
        
        if not self.username or not self.password:
            raise ValueError("EARTHDATA_USERNAME and EARTHDATA_PASSWORD must be provided")
        
        # Authenticate with Earthdata
        self._authenticate()
        
        # Initialize data source clients
        self.tempo_client = TEMPOClient(username, password)
        self.pandora_client = PandoraClient()
        self.tolnet_client = TOLNetClient()
        self.airnow_client = AirNowClient()
    
    def _authenticate(self):
        """Authenticate with Earthdata using provided credentials."""
        try:
            earthaccess.login(
                username=self.username,
                password=self.password
            )
            logger.info("Successfully authenticated with NASA Earthdata")
        except Exception as e:
            logger.error(f"Failed to authenticate with NASA Earthdata: {e}")
            raise
    
    def get_air_quality_data(
        self,
        city: str,
        parameters: List[str] = None,
        days_back: int = 7,
        sources: List[str] = None
    ) -> Dict[str, Any]:
        """
        Get air quality data from multiple NASA sources.
        
        Args:
            city: City name to fetch data for
            parameters: List of parameters to fetch
            days_back: Number of days to look back
            sources: List of data sources to use
        
        Returns:
            Dictionary with aggregated data from all sources
        """
        if parameters is None:
            parameters = ["NO2", "O3", "HCHO", "PM2.5"]
        
        if sources is None:
            sources = ["tempo", "pandora", "tolnet", "airnow"]
        
        all_measurements = []
        source_results = {}
        
        # Get data from each source
        for source in sources:
            try:
                if source == "tempo":
                    measurements = self._get_tempo_data(city, parameters, days_back)
                elif source == "pandora":
                    measurements = self._get_pandora_data(city, parameters, days_back)
                elif source == "tolnet":
                    measurements = self._get_tolnet_data(city, parameters, days_back)
                elif source == "airnow":
                    measurements = self._get_airnow_data(city, parameters, days_back)
                else:
                    logger.warning(f"Unknown data source: {source}")
                    continue
                
                source_results[source] = {
                    'measurements': measurements,
                    'count': len(measurements)
                }
                all_measurements.extend(measurements)
                
            except Exception as e:
                logger.error(f"Error fetching data from {source}: {e}")
                source_results[source] = {
                    'measurements': [],
                    'count': 0,
                    'error': str(e)
                }
        
        return {
            'all_measurements': all_measurements,
            'source_results': source_results,
            'total_measurements': len(all_measurements),
            'city': city,
            'parameters': parameters,
            'days_back': days_back
        }
    
    def _get_tempo_data(self, city: str, parameters: List[str], days_back: int) -> List[Dict[str, Any]]:
        """Get TEMPO satellite data."""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)
            
            # Search for TEMPO data
            granules = self.tempo_client.search_tempo_data(
                start_date=start_date,
                end_date=end_date,
                parameters=parameters
            )
            
            if not granules:
                return []
            
            # Download and process data
            tempo_data = self.tempo_client.download_tempo_data(granules)
            return tempo_data.get('measurements', [])
            
        except Exception as e:
            logger.error(f"Error getting TEMPO data: {e}")
            return []
    
    def _get_pandora_data(self, city: str, parameters: List[str], days_back: int) -> List[Dict[str, Any]]:
        """Get Pandora ground station data."""
        try:
            return self.pandora_client.get_measurements(
                city=city,
                parameters=parameters,
                days_back=days_back
            )
        except Exception as e:
            logger.error(f"Error getting Pandora data: {e}")
            return []
    
    def _get_tolnet_data(self, city: str, parameters: List[str], days_back: int) -> List[Dict[str, Any]]:
        """Get TOLNet ground station data."""
        try:
            return self.tolnet_client.get_measurements(
                city=city,
                parameters=parameters,
                days_back=days_back
            )
        except Exception as e:
            logger.error(f"Error getting TOLNet data: {e}")
            return []
    
    def _get_airnow_data(self, city: str, parameters: List[str], days_back: int) -> List[Dict[str, Any]]:
        """Get AirNow data."""
        try:
            return self.airnow_client.get_measurements(
                city=city,
                parameters=parameters,
                days_back=days_back
            )
        except Exception as e:
            logger.error(f"Error getting AirNow data: {e}")
            return []

class TEMPOClient:
    """Client for NASA TEMPO satellite data."""
    
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
    
    def search_tempo_data(
        self,
        start_date: datetime,
        end_date: datetime,
        bbox: List[float] = None,
        parameters: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for TEMPO Level 2 data."""
        if parameters is None:
            parameters = ["NO2", "O3", "HCHO", "H2CO"]
        
        if bbox is None:
            # Default to North America bounding box
            bbox = [-180, 15, -50, 70]
        
        try:
            logger.info(f"Searching TEMPO data from {start_date} to {end_date}")
            
            # Search for TEMPO Level 2 data
            results = earthaccess.search_data(
                short_name="TEMPO_L2",
                temporal=(start_date, end_date),
                bounding_box=bbox,
                count=100
            )
            
            logger.info(f"Found {len(results)} TEMPO granules")
            return results
            
        except Exception as e:
            logger.error(f"Error searching TEMPO data: {e}")
            return []
    
    def download_tempo_data(
        self,
        granules: List[Dict[str, Any]],
        download_path: str = "data/tempo/",
        parameters: List[str] = None
    ) -> Dict[str, Any]:
        """Download and process TEMPO data."""
        if parameters is None:
            parameters = ["NO2", "O3", "HCHO", "H2CO"]
        
        os.makedirs(download_path, exist_ok=True)
        
        try:
            # Download files
            files = earthaccess.download(granules, download_path)
            
            # Process files
            measurements = []
            for file_path in files:
                try:
                    file_measurements = self._process_tempo_file(file_path, parameters)
                    measurements.extend(file_measurements)
                except Exception as e:
                    logger.error(f"Error processing TEMPO file {file_path}: {e}")
                    continue
            
            return {
                'files': files,
                'download_path': download_path,
                'measurements': measurements,
                'records_processed': len(measurements)
            }
            
        except Exception as e:
            logger.error(f"Error downloading TEMPO data: {e}")
            return {
                'files': [],
                'download_path': download_path,
                'measurements': [],
                'records_processed': 0,
                'error': str(e)
            }
    
    def _process_tempo_file(self, file_path: str, parameters: List[str]) -> List[Dict[str, Any]]:
        """Process a single TEMPO NetCDF file."""
        measurements = []
        
        try:
            # Open NetCDF file
            ds = xr.open_dataset(file_path)
            
            # Get coordinates
            lats = ds.latitude.values
            lons = ds.longitude.values
            times = ds.time.values
            
            # Process each parameter
            for param in parameters:
                if param not in ds.variables:
                    continue
                
                param_data = ds[param].values
                valid_mask = ~np.isnan(param_data)
                
                if not np.any(valid_mask):
                    continue
                
                # Extract measurements
                valid_indices = np.where(valid_mask)
                
                for i, j, k in zip(valid_indices[0], valid_indices[1], valid_indices[2]):
                    try:
                        lat = float(lats[i, j])
                        lon = float(lons[i, j])
                        time_val = times[k]
                        value = float(param_data[i, j, k])
                        
                        # Convert time to datetime
                        if hasattr(time_val, 'item'):
                            time_val = time_val.item()
                        
                        if isinstance(time_val, np.datetime64):
                            dt = pd.to_datetime(time_val).to_pydatetime()
                        else:
                            dt = datetime.fromisoformat(str(time_val))
                        
                        # Determine city based on coordinates
                        city = self._get_city_from_coords(lat, lon)
                        
                        # Map TEMPO parameters
                        param_mapping = {
                            'NO2': 'NO2',
                            'O3': 'O3',
                            'HCHO': 'HCHO',
                            'H2CO': 'HCHO'
                        }
                        mapped_param = param_mapping.get(param, param)
                        
                        measurement = {
                            'city': city,
                            'parameter': mapped_param,
                            'value': value,
                            'unit': 'mol/m²',
                            'date_utc': dt,
                            'source': 'tempo',
                            'latitude': lat,
                            'longitude': lon
                        }
                        
                        measurements.append(measurement)
                        
                    except Exception as e:
                        logger.error(f"Error processing measurement: {e}")
                        continue
            
            ds.close()
            
        except Exception as e:
            logger.error(f"Error processing TEMPO file {file_path}: {e}")
        
        return measurements
    
    def _get_city_from_coords(self, lat: float, lon: float) -> str:
        """Determine city from coordinates."""
        # Simplified city mapping for North America
        city_mapping = [
            (40.7128, -74.0060, "New York"),
            (34.0522, -118.2437, "Los Angeles"),
            (41.8781, -87.6298, "Chicago"),
            (29.7604, -95.3698, "Houston"),
            (33.4484, -112.0740, "Phoenix"),
            (39.9526, -75.1652, "Philadelphia"),
            (32.7767, -96.7970, "Dallas"),
            (37.7749, -122.4194, "San Francisco"),
            (39.7392, -104.9903, "Denver"),
            (47.6062, -122.3321, "Seattle"),
        ]
        
        min_distance = float('inf')
        closest_city = "Unknown"
        
        for city_lat, city_lon, city_name in city_mapping:
            distance = ((lat - city_lat) ** 2 + (lon - city_lon) ** 2) ** 0.5
            if distance < min_distance:
                min_distance = distance
                closest_city = city_name
        
        return closest_city

class PandoraClient:
    """Client for NASA Pandora ground station data."""
    
    def __init__(self):
        self.base_url = "https://pandonia.net"
    
    def get_measurements(
        self,
        city: str,
        parameters: List[str],
        days_back: int
    ) -> List[Dict[str, Any]]:
        """Get Pandora measurements."""
        # Implementation for Pandora data access
        # This would connect to the Pandora API
        logger.info(f"Getting Pandora data for {city}")
        return []

class TOLNetClient:
    """Client for NASA TOLNet ground station data."""
    
    def __init__(self):
        self.base_url = "https://www-air.larc.nasa.gov"
    
    def get_measurements(
        self,
        city: str,
        parameters: List[str],
        days_back: int
    ) -> List[Dict[str, Any]]:
        """Get TOLNet measurements."""
        # Implementation for TOLNet data access
        logger.info(f"Getting TOLNet data for {city}")
        return []

class AirNowClient:
    """Client for AirNow data (EPA/NOAA/NASA partnership)."""
    
    def __init__(self):
        self.base_url = "https://www.airnowapi.org"
        self.api_key = os.getenv('AIRNOW_API_KEY')
    
    def get_measurements(
        self,
        city: str,
        parameters: List[str],
        days_back: int
    ) -> List[Dict[str, Any]]:
        """Get AirNow measurements."""
        if not self.api_key:
            logger.warning("AIRNOW_API_KEY not provided")
            return []
        
        # Implementation for AirNow data access
        logger.info(f"Getting AirNow data for {city}")
        return []
