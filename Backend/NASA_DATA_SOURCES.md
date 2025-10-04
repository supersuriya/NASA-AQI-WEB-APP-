# NASA Data Sources for AirSense

## Overview
The AirSense application now properly integrates with **NASA air quality data sources** as specified in the hackathon requirements. The application focuses on NASA data rather than third-party sources like OpenAQ.

## Primary NASA Data Sources

### 1. NASA TEMPO (Tropospheric Emissions: Monitoring of Pollution)
- **Primary satellite data source** for air quality monitoring
- **Parameters**: NO2, O3, HCHO, H2CO, Aerosol Index, PM
- **Coverage**: North America
- **Data Type**: Level 2 satellite products
- **Update Frequency**: Near Real-Time (NRT) data available
- **Access Method**: NASA Earthdata with earthaccess Python library

### 2. NASA Pandora Project
- **Ground station network** with 168 official sites globally
- **Technology**: Spectroscopy-based atmospheric composition measurements
- **Parameters**: O3, NO2, HCHO, and other trace gases
- **Coverage**: Global network
- **Data Type**: Ground-based observations
- **Access Method**: Pandonia Global Network API

### 3. NASA TOLNet (Tropospheric Ozone Lidar Network)
- **Specialized ozone monitoring** network
- **Sites**: 12 sites (3 fixed, 9 transportable)
- **Technology**: High spatio-temporal ozone observations using lidar
- **Parameters**: O3, NO2
- **Coverage**: North America
- **Data Type**: Ground-based lidar measurements
- **Access Method**: NASA TOLNet data portal

### 4. AirNow (EPA/NOAA/NASA Partnership)
- **Multi-agency ground station network**
- **Partners**: EPA, NOAA, NASA, CDC, National Park Service
- **Parameters**: PM2.5, PM10, O3, NO2, SO2, CO
- **Coverage**: United States
- **Data Type**: Real-time ground station measurements
- **Access Method**: AirNow API

## Data Integration Architecture

### Unified NASA Data Client
The application uses a `NASADataClient` that provides a unified interface to all NASA data sources:

```python
# Single endpoint for all NASA data sources
POST /ingest/nasa?city=New York&sources=tempo,pandora,tolnet,airnow
```

### Data Processing Pipeline
1. **Authentication**: NASA Earthdata credentials for satellite data access
2. **Data Retrieval**: Parallel fetching from multiple NASA sources
3. **Data Validation**: Comprehensive cleaning and unit conversion
4. **Data Storage**: Unified storage in SQLite database
5. **Machine Learning**: Training on combined NASA datasets

## NASA Data Access Requirements

### Required Credentials
- **NASA Earthdata Login**: Required for TEMPO, Pandora, and TOLNet data
- **AirNow API Key**: Optional for additional ground station data

### Data Access Methods
- **earthaccess**: Python library for NASA Earthdata access
- **Direct APIs**: For Pandora, TOLNet, and AirNow data
- **NetCDF Processing**: For satellite data files
- **Real-time Streaming**: For NRT data sources

## Parameters by Source

| Parameter | TEMPO | Pandora | TOLNet | AirNow |
|-----------|-------|---------|--------|--------|
| NO2 | ✅ | ✅ | ✅ | ✅ |
| O3 | ✅ | ✅ | ✅ | ✅ |
| HCHO | ✅ | ✅ | ❌ | ❌ |
| PM2.5 | ✅ | ❌ | ❌ | ✅ |
| PM10 | ❌ | ❌ | ❌ | ✅ |
| SO2 | ❌ | ❌ | ❌ | ✅ |
| CO | ❌ | ❌ | ❌ | ✅ |

## Implementation Details

### TEMPO Data Processing
- **File Format**: NetCDF Level 2 products
- **Spatial Resolution**: High-resolution satellite data
- **Temporal Coverage**: Near real-time + historical
- **Coordinate Mapping**: Automatic city assignment from lat/lon

### Ground Station Data
- **Pandora**: Spectroscopy measurements with high accuracy
- **TOLNet**: Lidar-based ozone profiling
- **AirNow**: Standard EPA monitoring parameters

### Data Quality Assurance
- **Unit Standardization**: All data converted to µg/m³ where applicable
- **Outlier Detection**: Statistical methods for data validation
- **Temporal Alignment**: Time series synchronization
- **Spatial Aggregation**: City-level data aggregation

## Benefits of NASA Data Integration

1. **Authoritative Sources**: Direct access to NASA's official air quality data
2. **Comprehensive Coverage**: Satellite + ground station data combination
3. **High Quality**: NASA's rigorous data validation and quality control
4. **Real-time Capability**: NRT data for current conditions
5. **Research Grade**: Data suitable for scientific analysis and forecasting
6. **Global Perspective**: Satellite data provides broader spatial coverage

## Usage Examples

### Ingest All NASA Sources
```bash
curl -X POST "http://localhost:8000/ingest/nasa?city=Los Angeles&sources=tempo,pandora,tolnet,airnow"
```

### Ingest Only Satellite Data
```bash
curl -X POST "http://localhost:8000/ingest/nasa?city=Chicago&sources=tempo"
```

### Ingest Only Ground Stations
```bash
curl -X POST "http://localhost:8000/ingest/nasa?city=New York&sources=pandora,tolnet,airnow"
```

## Future Enhancements

1. **Additional NASA Missions**: Integration with other NASA air quality missions
2. **Data Fusion**: Advanced algorithms for combining satellite and ground data
3. **Spatial Interpolation**: Gridded data products for better coverage
4. **Real-time Alerts**: Integration with NASA's alert systems
5. **Visualization**: NASA Worldview integration for data visualization

This implementation ensures that AirSense is fully compliant with the hackathon requirements to use NASA data sources for air quality forecasting.
