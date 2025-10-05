# Air Quality Data Ingestion API

A FastAPI backend module that fetches and ingests data from multiple APIs to prepare input for ML models predicting air quality. This system integrates NASA TOLNet, OpenAQ, and weather APIs to provide comprehensive air quality data for North American cities.

## 🚀 Features

- **Multi-Source Data Ingestion**: Fetches data from NASA TOLNet, OpenAQ, and weather APIs
- **Real-Time Data Processing**: Normalizes and stores data in SQLite database
- **ML-Ready Output**: Provides normalized JSON data ready for machine learning models
- **RESTful API**: Clean FastAPI endpoints for data access and configuration
- **Error Handling**: Robust error handling and logging throughout
- **Configurable Cities**: Easy city configuration and management

## 📊 Data Sources

### NASA TOLNet API
- **Base URL**: `https://tolnet.larc.nasa.gov/api/`
- **Authentication**: Earthdata Login (username/password)
- **Data**: Ozone (O3) measurements from ground stations
- **Coverage**: North American cities

### OpenAQ API
- **Base URL**: `https://api.openaq.org/v2/`
- **Authentication**: None required (public API)
- **Data**: NO₂, PM2.5, PM10, O₃, SO₂, CO measurements
- **Coverage**: Global ground station network

### Weather APIs
- **NASA Daymet**: Daily weather data
- **MERRA-2**: Atmospheric reanalysis data
- **Data**: Temperature, humidity, wind speed/direction, precipitation, pressure

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd air-quality-data-ingestion
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   Create a `.env` file with your NASA Earthdata credentials:
   ```env
   EARTHDATA_USERNAME=your_username
   EARTHDATA_PASSWORD=your_password
   DATABASE_URL=sqlite:///./air_quality_data.db
   ```

5. **Initialize the database**:
   ```bash
   python main.py
   ```

## 🚀 Quick Start

1. **Start the API server**:
   ```bash
   python main.py
   ```

2. **Test the API**:
   ```bash
   python test_api.py
   ```

3. **Access the API documentation**:
   - Open your browser to `http://localhost:8000/docs`
   - Interactive API documentation with Swagger UI

## 📡 API Endpoints

### Core Endpoints

- **`GET /`** - API information and available endpoints
- **`GET /health`** - Health check endpoint
- **`GET /ingest/data`** - Fetch and store data from all APIs
- **`GET /data/preview`** - Preview recent database records
- **`GET /data/normalized`** - Get ML-ready normalized data
- **`GET /data/stats`** - Data statistics and monitoring

### Configuration Endpoints

- **`GET /config/cities`** - Get all configured cities
- **`POST /config/cities`** - Add or update city configuration

## 🗄️ Database Schema

### Measurements Table
```sql
CREATE TABLE measurements (
    id INTEGER PRIMARY KEY,
    city VARCHAR(100) NOT NULL,
    parameter VARCHAR(50) NOT NULL,  -- NO2, PM2.5, O3, etc.
    value FLOAT NOT NULL,
    unit VARCHAR(20) NOT NULL,       -- µg/m³, ppm, etc.
    datetime_utc DATETIME NOT NULL,
    source VARCHAR(50) NOT NULL,     -- tolnet, openaq, etc.
    latitude FLOAT,
    longitude FLOAT,
    raw_data TEXT,                   -- Original API response
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Weather Table
```sql
CREATE TABLE weather (
    id INTEGER PRIMARY KEY,
    city VARCHAR(100) NOT NULL,
    temperature FLOAT,               -- Celsius
    humidity FLOAT,                  -- Percentage
    wind_speed FLOAT,                -- m/s
    wind_direction FLOAT,            -- Degrees
    precipitation FLOAT,             -- mm
    pressure FLOAT,                  -- hPa
    datetime_utc DATETIME NOT NULL,
    source VARCHAR(50) NOT NULL,     -- daymet, merra2, etc.
    latitude FLOAT,
    longitude FLOAT,
    raw_data TEXT,                   -- Original API response
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 🔧 Configuration

### City Configuration
Edit `config.json` to add or modify target cities:

```json
{
  "cities": [
    {
      "name": "New York",
      "latitude": 40.7128,
      "longitude": -74.0060,
      "timezone": "America/New_York"
    }
  ],
  "ingestion_settings": {
    "days_back": 7,
    "update_frequency_hours": 6,
    "retry_attempts": 3,
    "timeout_seconds": 30
  }
}
```

### Data Source Configuration
Enable/disable data sources in `config.json`:

```json
{
  "data_sources": {
    "tolnet": {
      "enabled": true,
      "base_url": "https://tolnet.larc.nasa.gov/api/",
      "parameters": ["O3_Number_Density"]
    },
    "openaq": {
      "enabled": true,
      "base_url": "https://api.openaq.org/v2/",
      "parameters": ["NO2", "PM2.5", "PM10", "O3"]
    },
    "weather": {
      "enabled": true,
      "sources": ["daymet", "merra2"],
      "parameters": ["temperature", "humidity", "wind_speed", "wind_direction", "precipitation"]
    }
  }
}
```

## 📊 Data Processing

### Unit Normalization
All measurements are normalized to standard units:
- **Air Quality**: µg/m³ (micrograms per cubic meter)
- **Temperature**: Celsius
- **Wind Speed**: m/s (meters per second)
- **Precipitation**: mm (millimeters)
- **Pressure**: hPa (hectopascals)

### Data Fusion
The system merges data from multiple sources:
- **Spatial Matching**: Finds closest city for each measurement
- **Temporal Alignment**: Groups data by timestamp
- **Quality Control**: Handles missing values and outliers

### ML-Ready Output
Normalized data is structured for machine learning:
```json
{
  "city_name": {
    "2024-01-01T12:00:00": {
      "measurements": {
        "PM2.5": {"value": 15.2, "unit": "µg/m³", "source": "openaq"},
        "NO2": {"value": 25.8, "unit": "µg/m³", "source": "openaq"},
        "O3": {"value": 45.3, "unit": "µg/m³", "source": "tolnet"}
      },
      "weather": {
        "temperature": 22.5,
        "humidity": 65.0,
        "wind_speed": 3.2,
        "wind_direction": 180.0,
        "precipitation": 0.0,
        "pressure": 1013.2
      }
    }
  }
}
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_api.py
```

The test suite covers:
- Health checks
- Data ingestion
- City configuration
- Data preview and statistics
- Normalized data output

## 📈 Monitoring

### Data Statistics
Access real-time data statistics:

```bash
curl http://localhost:8000/data/stats
```

### Health Monitoring
Check API health and status:

```bash
curl http://localhost:8000/health
```

## 🔒 Security

- **Environment Variables**: Sensitive credentials stored in `.env`
- **Input Validation**: Pydantic models validate all inputs
- **Error Handling**: Comprehensive error handling and logging
- **CORS**: Configured for cross-origin requests

## 🚀 Deployment

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "main.py"]
```

### Environment Variables
```env
EARTHDATA_USERNAME=your_username
EARTHDATA_PASSWORD=your_password
DATABASE_URL=sqlite:///./air_quality_data.db
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

## 📝 Usage Examples

### Fetch Data for All Cities
```bash
curl "http://localhost:8000/ingest/data?days_back=7"
```

### Get Normalized Data for ML
```bash
curl "http://localhost:8000/data/normalized?city=New York&days_back=7"
```

### Add New City
```bash
curl -X POST "http://localhost:8000/config/cities" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Chicago",
    "latitude": 41.8781,
    "longitude": -87.6298,
    "timezone": "America/Chicago"
  }'
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the API documentation at `/docs`
2. Review the test suite in `test_api.py`
3. Check the logs for error details
4. Open an issue on GitHub

## 🔮 Future Enhancements

- [ ] Real-time WebSocket updates
- [ ] Additional data sources (PurpleAir, AirNow)
- [ ] Advanced data quality metrics
- [ ] Automated data validation
- [ ] Cloud deployment configurations
- [ ] Machine learning model integration