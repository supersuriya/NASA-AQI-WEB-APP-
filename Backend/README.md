# AirSense - Air Quality Forecasting API

A FastAPI application that integrates NASA air quality data sources (TEMPO, Pandora, TOLNet, AirNow) to forecast air quality for North American cities using machine learning.

## Features

- **Data Integration**: Fetches air quality data from NASA sources (TEMPO, Pandora, TOLNet, AirNow)
- **Machine Learning Forecasting**: Uses RandomForestRegressor to predict PM2.5 levels for the next 24 hours
- **RESTful API**: Clean FastAPI endpoints for data ingestion and forecasting
- **Background Processing**: Automated weekly model retraining using APScheduler
- **Data Validation**: Comprehensive data cleaning and validation using Pydantic
- **Docker Support**: Containerized deployment with Docker

## API Endpoints

### Core Endpoints

- `GET /` - API information and available endpoints
- `GET /health` - Health check endpoint
- `POST /ingest/nasa` - Ingest data from NASA sources (TEMPO, Pandora, TOLNet, AirNow)
- `POST /forecast` - Generate air quality forecasts
- `GET /measurements` - Retrieve recent measurements
- `POST /train-model` - Train ML model for specific city/parameter

### Example Usage

#### Health Check
```bash
curl http://localhost:8000/health
```

#### Ingest NASA Data
```bash
curl -X POST "http://localhost:8000/ingest/nasa?city=New York&days_back=7&sources=tempo,pandora"
```

#### Generate Forecast
```bash
curl -X POST "http://localhost:8000/forecast" \
  -H "Content-Type: application/json" \
  -d '{"city": "New York", "parameter": "PM2.5", "hours_ahead": 24}'
```

## Installation

### Using Docker (Recommended)

1. Clone the repository
2. Copy `env.example` to `.env` and configure your environment variables
3. Build and run with Docker:

```bash
docker build -t airsense .
docker run -p 8000:8000 --env-file .env airsense
```

### Local Development

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp env.example .env
# Edit .env with your configuration
```

4. Run the application:
```bash
python main.py
```

## Environment Variables

Required:
- `EARTHDATA_USERNAME` - NASA Earthdata username for TEMPO access
- `EARTHDATA_PASSWORD` - NASA Earthdata password

Optional:
- `DATABASE_URL` - Database connection string (default: SQLite)
- `API_HOST` - API host (default: 0.0.0.0)
- `API_PORT` - API port (default: 8000)
- `LOG_LEVEL` - Logging level (default: INFO)

## Data Sources

### NASA TEMPO (Primary)
- Tropospheric Emissions: Monitoring of Pollution
- Level 2 satellite data products for air quality pollutants
- Parameters: NO2, O3, HCHO, H2CO, Aerosol Index, PM
- Coverage: North America
- Near Real-Time (NRT) data available

### NASA Pandora Project
- Ground station network with 168 official sites
- Spectroscopy-based atmospheric composition measurements
- Parameters: O3, NO2, HCHO, and other trace gases
- Coverage: Global network

### NASA TOLNet
- Tropospheric Ozone Lidar Network
- 12 sites (3 fixed, 9 transportable)
- High spatio-temporal ozone observations
- Parameters: O3, NO2
- Coverage: North America

### AirNow (EPA/NOAA/NASA Partnership)
- Ground station network data
- Real-time air quality measurements
- Parameters: PM2.5, PM10, O3, NO2, SO2, CO
- Coverage: United States

## Machine Learning Model

- **Algorithm**: RandomForestRegressor
- **Features**: Time-based features, lagged values, rolling averages
- **Retraining**: Weekly automatic retraining
- **Validation**: Cross-validation with MAE and R² metrics

## Project Structure

```
├── main.py                 # FastAPI application
├── database.py            # SQLAlchemy database configuration
├── models.py              # SQLAlchemy ORM models
├── schemas.py             # Pydantic schemas for validation
├── ml_model.py            # Machine learning model implementation
├── utils/                 # Utility modules
│   ├── openaq_client.py   # OpenAQ API client
│   ├── tempo_client.py    # NASA TEMPO client
│   └── data_processor.py  # Data cleaning and validation
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
└── env.example           # Environment variables template
```

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black .
isort .
```

### Type Checking
```bash
mypy .
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For questions or issues, please open an issue on GitHub.
