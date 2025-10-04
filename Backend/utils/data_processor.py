"""
Data processing utilities for cleaning and validating air quality data.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class DataProcessor:
    """
    Utility class for processing and cleaning air quality data.
    """
    
    # Parameter-specific validation ranges (in µg/m³ unless specified)
    PARAMETER_RANGES = {
        'PM2.5': (0, 500),  # µg/m³
        'O3': (0, 500),     # µg/m³
        'NO2': (0, 500),    # µg/m³
        'HCHO': (0, 50),    # µg/m³
    }
    
    # Unit conversion factors to µg/m³
    UNIT_CONVERSIONS = {
        'µg/m³': 1.0,
        'ug/m3': 1.0,
        'mg/m³': 1000.0,
        'mg/m3': 1000.0,
        'ppm': None,  # Requires molecular weight conversion
        'ppb': None,  # Requires molecular weight conversion
        'mol/m²': None,  # TEMPO specific unit
    }
    
    # Molecular weights for ppm/ppb conversion (g/mol)
    MOLECULAR_WEIGHTS = {
        'PM2.5': 1.0,  # Not applicable for PM2.5
        'O3': 48.0,
        'NO2': 46.0,
        'HCHO': 30.0,
    }
    
    @classmethod
    def clean_measurements(cls, measurements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Clean and validate a list of measurements.
        
        Args:
            measurements: List of measurement dictionaries
        
        Returns:
            List of cleaned and validated measurements
        """
        cleaned = []
        
        for measurement in measurements:
            try:
                cleaned_measurement = cls._clean_single_measurement(measurement)
                if cleaned_measurement:
                    cleaned.append(cleaned_measurement)
            except Exception as e:
                logger.error(f"Error cleaning measurement: {e}")
                continue
        
        logger.info(f"Cleaned {len(cleaned)} out of {len(measurements)} measurements")
        return cleaned
    
    @classmethod
    def _clean_single_measurement(cls, measurement: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Clean and validate a single measurement.
        """
        try:
            # Extract and validate required fields
            city = measurement.get('city', '').strip()
            parameter = measurement.get('parameter', '').strip()
            value = measurement.get('value')
            unit = measurement.get('unit', '').strip()
            date_utc = measurement.get('date_utc')
            source = measurement.get('source', 'unknown')
            
            # Validate required fields
            if not city or not parameter or value is None or not unit or not date_utc:
                return None
            
            # Convert value to float
            try:
                value = float(value)
            except (ValueError, TypeError):
                return None
            
            # Validate date
            if isinstance(date_utc, str):
                try:
                    date_utc = datetime.fromisoformat(date_utc.replace('Z', '+00:00'))
                except ValueError:
                    return None
            elif not isinstance(date_utc, datetime):
                return None
            
            # Check if date is reasonable (not too far in past or future)
            now = datetime.utcnow()
            if date_utc < now - timedelta(days=365) or date_utc > now + timedelta(days=1):
                return None
            
            # Convert units to µg/m³
            converted_value, converted_unit = cls._convert_units(value, unit, parameter)
            if converted_value is None:
                return None
            
            # Validate value range
            if not cls._validate_value_range(converted_value, parameter):
                return None
            
            # Normalize parameter name
            normalized_param = cls._normalize_parameter_name(parameter)
            
            return {
                'city': city,
                'parameter': normalized_param,
                'value': converted_value,
                'unit': converted_unit,
                'date_utc': date_utc,
                'source': source,
                'original_data': measurement
            }
            
        except Exception as e:
            logger.error(f"Error cleaning measurement: {e}")
            return None
    
    @classmethod
    def _convert_units(cls, value: float, unit: str, parameter: str) -> Tuple[Optional[float], str]:
        """
        Convert units to µg/m³.
        
        Returns:
            Tuple of (converted_value, converted_unit) or (None, None) if conversion fails
        """
        unit = unit.lower().strip()
        
        # Direct conversion factors
        if unit in cls.UNIT_CONVERSIONS:
            factor = cls.UNIT_CONVERSIONS[unit]
            if factor is not None:
                return value * factor, 'µg/m³'
        
        # Special handling for ppm/ppb
        if unit in ['ppm', 'ppb']:
            return cls._convert_ppm_ppb(value, unit, parameter)
        
        # Special handling for TEMPO units
        if unit in ['mol/m²', 'mol/m2']:
            # This is a simplified conversion - in reality, you'd need more complex calculations
            # For now, we'll just return the value as-is with a note
            return value, unit
        
        # Unknown unit - return as-is
        logger.warning(f"Unknown unit '{unit}' for parameter '{parameter}'")
        return value, unit
    
    @classmethod
    def _convert_ppm_ppb(cls, value: float, unit: str, parameter: str) -> Tuple[Optional[float], str]:
        """
        Convert ppm/ppb to µg/m³ using molecular weight.
        This is a simplified conversion assuming standard temperature and pressure.
        """
        if parameter not in cls.MOLECULAR_WEIGHTS:
            logger.warning(f"No molecular weight available for parameter '{parameter}'")
            return None, unit
        
        # Conversion factor: 1 ppm = 1 mg/m³ at STP
        # 1 ppb = 0.001 ppm
        if unit == 'ppm':
            factor = 1000  # ppm to µg/m³
        elif unit == 'ppb':
            factor = 1     # ppb to µg/m³
        else:
            return None, unit
        
        # Apply molecular weight adjustment
        molecular_weight = cls.MOLECULAR_WEIGHTS[parameter]
        converted_value = value * factor * molecular_weight
        
        return converted_value, 'µg/m³'
    
    @classmethod
    def _validate_value_range(cls, value: float, parameter: str) -> bool:
        """
        Validate that the value is within reasonable range for the parameter.
        """
        if parameter not in cls.PARAMETER_RANGES:
            return True  # Unknown parameter, don't validate
        
        min_val, max_val = cls.PARAMETER_RANGES[parameter]
        return min_val <= value <= max_val
    
    @classmethod
    def _normalize_parameter_name(cls, parameter: str) -> str:
        """
        Normalize parameter names to standard format.
        """
        param_mapping = {
            'pm25': 'PM2.5',
            'pm2.5': 'PM2.5',
            'pm2_5': 'PM2.5',
            'o3': 'O3',
            'ozone': 'O3',
            'no2': 'NO2',
            'nitrogen_dioxide': 'NO2',
            'hcho': 'HCHO',
            'formaldehyde': 'HCHO',
            'h2co': 'HCHO',
        }
        
        normalized = param_mapping.get(parameter.lower().strip(), parameter.upper())
        return normalized
    
    @classmethod
    def detect_outliers(cls, measurements: List[Dict[str, Any]], 
                       parameter: str, method: str = 'iqr') -> List[Dict[str, Any]]:
        """
        Detect outliers in measurements using specified method.
        
        Args:
            measurements: List of measurement dictionaries
            parameter: Parameter to analyze
            method: Outlier detection method ('iqr', 'zscore', 'modified_zscore')
        
        Returns:
            List of measurements with outlier flag
        """
        if not measurements:
            return measurements
        
        # Filter measurements for the specific parameter
        param_measurements = [m for m in measurements if m.get('parameter') == parameter]
        
        if len(param_measurements) < 3:
            return measurements  # Not enough data for outlier detection
        
        # Extract values
        values = [m['value'] for m in param_measurements]
        
        # Detect outliers
        outlier_indices = set()
        
        if method == 'iqr':
            outlier_indices = cls._detect_outliers_iqr(values)
        elif method == 'zscore':
            outlier_indices = cls._detect_outliers_zscore(values)
        elif method == 'modified_zscore':
            outlier_indices = cls._detect_outliers_modified_zscore(values)
        
        # Mark outliers
        result = []
        for i, measurement in enumerate(measurements):
            measurement_copy = measurement.copy()
            if i in outlier_indices:
                measurement_copy['is_outlier'] = True
            else:
                measurement_copy['is_outlier'] = False
            result.append(measurement_copy)
        
        return result
    
    @classmethod
    def _detect_outliers_iqr(cls, values: List[float]) -> set:
        """Detect outliers using Interquartile Range method."""
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outlier_indices = set()
        for i, value in enumerate(values):
            if value < lower_bound or value > upper_bound:
                outlier_indices.add(i)
        
        return outlier_indices
    
    @classmethod
    def _detect_outliers_zscore(cls, values: List[float], threshold: float = 3.0) -> set:
        """Detect outliers using Z-score method."""
        mean = np.mean(values)
        std = np.std(values)
        
        if std == 0:
            return set()
        
        outlier_indices = set()
        for i, value in enumerate(values):
            z_score = abs((value - mean) / std)
            if z_score > threshold:
                outlier_indices.add(i)
        
        return outlier_indices
    
    @classmethod
    def _detect_outliers_modified_zscore(cls, values: List[float], threshold: float = 3.5) -> set:
        """Detect outliers using Modified Z-score method."""
        median = np.median(values)
        mad = np.median([abs(x - median) for x in values])
        
        if mad == 0:
            return set()
        
        outlier_indices = set()
        for i, value in enumerate(values):
            modified_z_score = 0.6745 * (value - median) / mad
            if abs(modified_z_score) > threshold:
                outlier_indices.add(i)
        
        return outlier_indices
    
    @classmethod
    def aggregate_measurements(cls, measurements: List[Dict[str, Any]], 
                             aggregation: str = 'hourly') -> List[Dict[str, Any]]:
        """
        Aggregate measurements by time period.
        
        Args:
            measurements: List of measurement dictionaries
            aggregation: Aggregation period ('hourly', 'daily')
        
        Returns:
            List of aggregated measurements
        """
        if not measurements:
            return measurements
        
        # Convert to DataFrame for easier aggregation
        df = pd.DataFrame(measurements)
        df['date_utc'] = pd.to_datetime(df['date_utc'])
        
        # Group by city, parameter, and time period
        if aggregation == 'hourly':
            df['time_key'] = df['date_utc'].dt.floor('H')
        elif aggregation == 'daily':
            df['time_key'] = df['date_utc'].dt.floor('D')
        else:
            return measurements
        
        # Aggregate values
        grouped = df.groupby(['city', 'parameter', 'time_key']).agg({
            'value': 'mean',
            'unit': 'first',
            'source': 'first'
        }).reset_index()
        
        # Convert back to list of dictionaries
        aggregated = []
        for _, row in grouped.iterrows():
            aggregated.append({
                'city': row['city'],
                'parameter': row['parameter'],
                'value': float(row['value']),
                'unit': row['unit'],
                'date_utc': row['time_key'].to_pydatetime(),
                'source': row['source']
            })
        
        return aggregated
