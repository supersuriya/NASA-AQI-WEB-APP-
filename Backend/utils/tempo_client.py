"""
NASA TEMPO data client using earthaccess for AppEEARS API.
"""
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import earthaccess
import xarray as xr
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class TEMPOClient:
    """
    Client for accessing NASA TEMPO data through earthaccess.
    """
    
    def __init__(self, username: str = None, password: str = None):
        """
        Initialize TEMPO client with Earthdata credentials.
        
        Args:
            username: Earthdata username (from environment if not provided)
            password: Earthdata password (from environment if not provided)
        """
        self.username = username or os.getenv('EARTHDATA_USERNAME')
        self.password = password or os.getenv('EARTHDATA_PASSWORD')
        
        if not self.username or not self.password:
            raise ValueError("EARTHDATA_USERNAME and EARTHDATA_PASSWORD must be provided")
        
        # Authenticate with Earthdata
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Earthdata using provided credentials."""
        try:
            earthaccess.login(
                username=self.username,
                password=self.password
            )
            logger.info("Successfully authenticated with Earthdata")
        except Exception as e:
            logger.error(f"Failed to authenticate with Earthdata: {e}")
            raise
    
    def search_tempo_data(
        self,
        start_date: datetime,
        end_date: datetime,
        bbox: List[float] = None,  # [west, south, east, north]
        parameters: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for TEMPO Level 2 data.
        
        Args:
            start_date: Start date for data search
            end_date: End date for data search
            bbox: Bounding box for spatial filtering [west, south, east, north]
            parameters: List of parameters to search for
        
        Returns:
            List of granule information
        """
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
                count=100  # Limit results
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
        """
        Download TEMPO data files.
        
        Args:
            granules: List of granule information from search
            download_path: Local path to save downloaded files
            parameters: List of parameters to extract
        
        Returns:
            Dictionary with download results
        """
        if parameters is None:
            parameters = ["NO2", "O3", "HCHO", "H2CO"]
        
        # Create download directory
        os.makedirs(download_path, exist_ok=True)
        
        downloaded_files = []
        processed_measurements = []
        
        try:
            logger.info(f"Downloading {len(granules)} TEMPO granules to {download_path}")
            
            # Download files
            files = earthaccess.download(granules, download_path)
            downloaded_files.extend(files)
            
            logger.info(f"Downloaded {len(files)} files")
            
            # Process each downloaded file
            for file_path in files:
                try:
                    measurements = self._process_tempo_file(file_path, parameters)
                    processed_measurements.extend(measurements)
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")
                    continue
            
            return {
                'files': downloaded_files,
                'download_path': download_path,
                'measurements': processed_measurements,
                'records_processed': len(processed_measurements)
            }
            
        except Exception as e:
            logger.error(f"Error downloading TEMPO data: {e}")
            return {
                'files': downloaded_files,
                'download_path': download_path,
                'measurements': processed_measurements,
                'records_processed': len(processed_measurements),
                'error': str(e)
            }
    
    def _process_tempo_file(self, file_path: str, parameters: List[str]) -> List[Dict[str, Any]]:
        """
        Process a single TEMPO NetCDF file and extract measurements.
        """
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
                    logger.warning(f"Parameter {param} not found in file {file_path}")
                    continue
                
                # Get parameter data
                param_data = ds[param].values
                
                # Get valid data (not NaN)
                valid_mask = ~np.isnan(param_data)
                
                if not np.any(valid_mask):
                    continue
                
                # Get valid indices
                valid_indices = np.where(valid_mask)
                
                # Extract measurements
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
                        
                        # Determine city based on coordinates (simplified)
                        city = self._get_city_from_coords(lat, lon)
                        
                        # Map TEMPO parameters to standard names
                        param_mapping = {
                            'NO2': 'NO2',
                            'O3': 'O3',
                            'HCHO': 'HCHO',
                            'H2CO': 'HCHO'  # Map H2CO to HCHO
                        }
                        mapped_param = param_mapping.get(param, param)
                        
                        measurement = {
                            'city': city,
                            'parameter': mapped_param,
                            'value': value,
                            'unit': 'mol/m²',  # TEMPO units
                            'date_utc': dt,
                            'source': 'tempo',
                            'latitude': lat,
                            'longitude': lon,
                            'raw_data': {
                                'file_path': file_path,
                                'original_parameter': param
                            }
                        }
                        
                        measurements.append(measurement)
                        
                    except Exception as e:
                        logger.error(f"Error processing measurement at ({i}, {j}, {k}): {e}")
                        continue
            
            ds.close()
            
        except Exception as e:
            logger.error(f"Error processing TEMPO file {file_path}: {e}")
        
        return measurements
    
    def _get_city_from_coords(self, lat: float, lon: float) -> str:
        """
        Determine city name from latitude and longitude coordinates.
        This is a simplified implementation - in production, you'd use a proper geocoding service.
        """
        # Simple coordinate-based city mapping for North America
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
            (25.7617, -80.1918, "Miami"),
            (42.3601, -71.0589, "Boston"),
            (43.6532, -79.3832, "Toronto"),
            (45.5017, -73.5673, "Montreal"),
            (49.2827, -123.1207, "Vancouver"),
        ]
        
        # Find closest city (simplified distance calculation)
        min_distance = float('inf')
        closest_city = "Unknown"
        
        for city_lat, city_lon, city_name in city_mapping:
            distance = ((lat - city_lat) ** 2 + (lon - city_lon) ** 2) ** 0.5
            if distance < min_distance:
                min_distance = distance
                closest_city = city_name
        
        return closest_city
    
    def get_recent_tempo_data(
        self,
        days_back: int = 7,
        parameters: List[str] = None
    ) -> Dict[str, Any]:
        """
        Get recent TEMPO data for the last N days.
        
        Args:
            days_back: Number of days to look back
            parameters: List of parameters to fetch
        
        Returns:
            Dictionary with processed measurements
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        
        # Search for data
        granules = self.search_tempo_data(start_date, end_date, parameters=parameters)
        
        if not granules:
            logger.warning("No TEMPO granules found for the specified time period")
            return {
                'files': [],
                'download_path': '',
                'measurements': [],
                'records_processed': 0
            }
        
        # Download and process data
        return self.download_tempo_data(granules, parameters=parameters)
