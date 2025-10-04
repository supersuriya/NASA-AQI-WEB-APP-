# Backend - Cleaner, Safer Skies

This folder will contain the backend API for the NASA Air Quality Monitor project.

## Planned Structure

```
backend/
├── app.py                 # Main Flask/FastAPI application
├── models/               # Data models
├── services/             # Business logic
├── utils/                # Utility functions
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## API Endpoints

### Planned Endpoints

- `GET /api/predict?lat={lat}&lon={lon}` - Get air quality prediction for coordinates
- `GET /api/health` - Health check endpoint
- `GET /api/history?lat={lat}&lon={lon}&hours={hours}` - Get historical data

### Expected Response Format

```json
{
    "predicted_pm25": 22.5,
    "category": "Moderate",
    "source": "NASA Data",
    "timestamp": "2024-10-04T12:00:00Z",
    "confidence": 0.85
}
```

## Development Status

🚧 **Under Development** - Backend implementation coming soon!

The frontend is currently configured to use mock data. Once the backend is ready, simply change `useMock = false` in `frontend/script.js`.
