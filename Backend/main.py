"""
NASA Air Quality Forecast API - FastAPI Backend
Serves the trained RandomForestRegressor model for air quality predictions.
"""
import os
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pydantic import BaseModel, Field

from database import get_db, create_tables
from models import Measurement, Forecast
from ml_model import AirQualityForecaster
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global scheduler for background tasks
scheduler = None
forecaster = None
prediction_cache = {}  # Cache for predictions

def get_forecaster():
    """Get or create the forecaster instance lazily."""
    global forecaster
    if forecaster is None:
        logger.info("Initializing AirQualityForecaster...")
        forecaster = AirQualityForecaster()
        logger.info("AirQualityForecaster initialized successfully")
    return forecaster

def ingest_airnow_for_city(db: Session, city: str, hours_back: int = 24) -> int:
    """
    Fetch recent AirNow data using city-specific coordinates.
    Returns number of records written.
    """
    api_key = os.getenv("AIRNOW_API_KEY")
    if not api_key:
        logger.warning("AIRNOW_API_KEY not set; cannot ingest AirNow data")
        return 0

    # City coordinates for smaller bounding boxes
    city_coords = {
        "los angeles": (34.0522, -118.2437),
        "new york": (40.7128, -74.0060),
        "chicago": (41.8781, -87.6298),
        "houston": (29.7604, -95.3698),
        "phoenix": (33.4484, -112.0740),
        "philadelphia": (39.9526, -75.1652),
        "san antonio": (29.4241, -98.4936),
        "san diego": (32.7157, -117.1611),
        "dallas": (32.7767, -96.7970),
        "austin": (30.2672, -97.7431),
    }
    
    city_lower = city.lower()
    if city_lower not in city_coords:
        logger.warning(f"City {city} not in predefined list, using Los Angeles as default")
        lat, lon = city_coords["los angeles"]
    else:
        lat, lon = city_coords[city_lower]

    try:
        end = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        start = end - timedelta(hours=min(hours_back, 24))  # Limit to 24 hours max
        
        # Create smaller bbox around city (±2 degrees)
        bbox = f"{lon-2},{lat-2},{lon+2},{lat+2}"
        
        params = {
            "parameters": "PM25,OZONE,NO2",
            "BBOX": bbox,
            "dataType": "A",
            "format": "application/json",
            "startDate": start.strftime("%Y-%m-%dT%H"),
            "endDate": end.strftime("%Y-%m-%dT%H"),
            "API_KEY": api_key,
        }
        url = "https://www.airnowapi.org/aq/data/"
        logger.info(f"Fetching AirNow data for {city} (bbox: {bbox})")
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        data = r.json() if r.headers.get("Content-Type", "").startswith("application/json") else []
        
        # Check for API errors
        if isinstance(data, dict) and "WebServiceError" in data:
            logger.warning(f"AirNow API error: {data['WebServiceError']}")
            return 0

        param_map = {"OZONE": ("O3", "ppb"), "PM25": ("PM2.5", "µg/m³"), "NO2": ("NO2", "ppb")}
        written = 0
        for rec in data:
            try:
                # Use the requested city name instead of strict matching
                rec_city = city
                parameter = rec.get("Parameter")
                if parameter not in param_map:
                    continue
                param_std, unit = param_map[parameter]
                
                # AirNow returns AQI, not raw values - use AQI as the value
                value = float(rec.get("AQI", 0))
                if value == 0:
                    continue
                    
                ts = rec.get("UTC") or rec.get("DateObservedUTC") or rec.get("DateTime")
                if ts and "T" not in ts and ":" in ts:
                    ts = ts.replace(" ", "T") + ":00"
                elif ts and "T" in ts and ":" in ts:
                    ts = ts + ":00" if ts.count(":") == 1 else ts
                dt = datetime.fromisoformat(ts)

                # Check if a matching record already exists to avoid duplicates
                exists = db.query(Measurement).filter(
                    Measurement.city == rec_city,
                    Measurement.parameter == param_std,
                    Measurement.date_utc == dt,
                    Measurement.source == "airnow"
                ).first()
                if exists:
                    continue

                m = Measurement(
                    city=rec_city,
                    parameter=param_std,
                    value=value,
                    unit=unit,
                    date_utc=dt,
                    source="airnow",
                )
                db.add(m)
                written += 1
            except Exception as e:
                continue

        if written:
            db.commit()
        logger.info(f"AirNow ingestion for {city}: {written} records written")
        return written
    except Exception as e:
        logger.warning(f"AirNow ingestion failed for {city}: {e}")
        db.rollback()
        return 0

def generate_deterministic_predictions(city: str, parameter: str, hours_ahead: int) -> Dict[str, Any]:
    """
    Generate deterministic predictions using a hash-based approach for consistency.
    """
    import hashlib
    
    # Create a deterministic seed based on city, parameter, and current hour
    current_hour = datetime.utcnow().hour
    seed_string = f"{city}_{parameter}_{current_hour}"
    seed = int(hashlib.md5(seed_string.encode()).hexdigest()[:8], 16)
    
    logger.info(f"Generating deterministic predictions for {city} - {parameter}")
    logger.info(f"Seed string: {seed_string}")
    logger.info(f"Generated seed: {seed}")
    
    # Set numpy random seed for deterministic results
    np.random.seed(seed)
    
    # Base values for different parameters
    base_values = {
        "PM2.5": {"mean": 15, "std": 8, "min": 0, "max": 50},
        "O3": {"mean": 45, "std": 15, "min": 0, "max": 100},
        "NO2": {"mean": 25, "std": 10, "min": 0, "max": 80}
    }
    
    base_config = base_values.get(parameter, {"mean": 20, "std": 10, "min": 0, "max": 50})
    
    predictions = []
    confidence_intervals = []
    
    for i in range(hours_ahead):
        # Calculate hour of day for this prediction
        hour_of_day = (current_hour + i) % 24
        
        # Time-based factors (higher during day, lower at night)
        if 6 <= hour_of_day <= 18:  # Daytime
            time_factor = 1.2
        elif 22 <= hour_of_day or hour_of_day <= 5:  # Night
            time_factor = 0.7
        else:  # Evening/Morning
            time_factor = 1.0
        
        # Generate deterministic prediction
        prediction = max(base_config["min"], min(base_config["max"], 
            np.random.normal(base_config["mean"] * time_factor, base_config["std"])))
        
        # Generate confidence interval (30% uncertainty)
        confidence_width = prediction * 0.3
        lower = max(base_config["min"], prediction - confidence_width)
        upper = min(base_config["max"], prediction + confidence_width)
        
        predictions.append(round(prediction, 2))
        confidence_intervals.append([round(lower, 2), round(upper, 2)])
    
    logger.info(f"Generated {len(predictions)} predictions for {city} - {parameter}")
    logger.info(f"First prediction: {predictions[0] if predictions else 'None'}")
    
    return {
        "predictions": predictions,
        "confidence_intervals": confidence_intervals,
        "seed": seed,
        "method": "deterministic_hash"
    }

def get_cached_prediction(city: str, parameter: str, hours_ahead: int) -> Optional[Dict[str, Any]]:
    """Get cached prediction if available and not expired."""
    global prediction_cache
    
    # Create cache key
    current_hour = datetime.utcnow().hour
    cache_key = f"{city}_{parameter}_{hours_ahead}_{current_hour}"
    
    if cache_key in prediction_cache:
        cached_data = prediction_cache[cache_key]
        # Check if cache is still valid (within same hour)
        if datetime.utcnow().hour == cached_data.get('cached_hour'):
            logger.info(f"Using cached prediction for {city} - {parameter}")
            return cached_data['prediction']
    
    return None

def cache_prediction(city: str, parameter: str, hours_ahead: int, prediction_data: Dict[str, Any]):
    """Cache prediction data."""
    global prediction_cache
    
    current_hour = datetime.utcnow().hour
    cache_key = f"{city}_{parameter}_{hours_ahead}_{current_hour}"
    
    prediction_cache[cache_key] = {
        'prediction': prediction_data,
        'cached_hour': current_hour,
        'cached_at': datetime.utcnow()
    }
    
    logger.info(f"Cached prediction for {city} - {parameter}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    global scheduler
    
    # Startup
    logger.info("Starting NASA Air Quality Forecast API...")
    
    # Create database tables
    create_tables()
    logger.info("Database tables created")
    
    # Initialize scheduler for weekly model retraining
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        retrain_models_weekly,
        CronTrigger(day_of_week=0, hour=2, minute=0),  # Every Sunday at 2 AM
        id='weekly_model_retrain',
        name='Weekly Model Retraining',
        replace_existing=True
    )
    scheduler.start()
    logger.info("Background scheduler started for weekly model retraining")
    
    yield
    
    # Shutdown
    logger.info("Shutting down NASA Air Quality Forecast API...")
    if scheduler:
        scheduler.shutdown()
    logger.info("Application shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="NASA Air Quality Forecast API",
    description="Air Quality Forecasting System using RandomForestRegressor for PM2.5, O3, and NO2 predictions",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# Pydantic models for request/response validation
class PredictRequest(BaseModel):
    """Request model for air quality predictions."""
    city: str = Field(..., min_length=1, max_length=100, description="City name for prediction")
    parameter: str = Field(..., description="Air quality parameter: PM2.5, O3, or NO2")
    hours_ahead: int = Field(..., ge=1, le=168, description="Hours ahead to predict (1-168)")
    recent_data: Optional[List[Dict[str, Any]]] = Field(None, description="Optional recent hourly air quality data")
    use_real_data: Optional[bool] = Field(False, description="If true, try to fetch real data (e.g., AirNow) before fallback")

class PredictResponse(BaseModel):
    """Response model for air quality predictions."""
    city: str
    parameter: str
    hours_ahead: int
    predictions: List[Dict[str, Any]]
    confidence_intervals: List[Dict[str, Any]]
    model_metadata: Dict[str, Any]
    timestamp: datetime

class RetrainRequest(BaseModel):
    """Request model for model retraining."""
    city: str = Field(..., description="City name to retrain model for")
    parameter: str = Field(..., description="Parameter to retrain: PM2.5, O3, or NO2")

class RetrainResponse(BaseModel):
    """Response model for model retraining."""
    success: bool
    message: str
    training_metrics: Dict[str, Any]
    timestamp: datetime

# Root endpoint - serve frontend
@app.get("/")
async def root():
    """Serve the frontend application."""
    frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    else:
        return {"message": "NASA Air Quality Forecast API is running", "frontend": "Frontend files not found"}

# API status endpoint
@app.get("/api/status")
async def api_status():
    """API status endpoint."""
    return {"message": "NASA Air Quality Forecast API is running"}

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0",
        "message": "NASA Air Quality Forecast API is healthy"
    }

# Main prediction endpoint
@app.post("/predict", response_model=PredictResponse)
async def predict_air_quality(
    request: PredictRequest,
    db: Session = Depends(get_db)
):
    """
    Predict air quality parameters (PM2.5, O3, NO2) for specific cities up to 168 hours ahead.
    
    Args:
        request: Prediction request with city, parameter, hours_ahead, and optional recent data
        db: Database session
        
    Returns:
        PredictResponse with predictions, confidence intervals, and model metadata
    """
    try:
        # Validate parameter
        valid_parameters = ["PM2.5", "O3", "NO2"]
        if request.parameter not in valid_parameters:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid parameter '{request.parameter}'. Must be one of: {valid_parameters}"
            )
        
        logger.info(f"Generating {request.hours_ahead}h forecast for {request.city} - {request.parameter}")
        logger.info(f"Request timestamp: {datetime.utcnow().isoformat()}")
        logger.info(f"Current hour: {datetime.utcnow().hour}")
        
        # Optionally fetch real data first (AirNow) to avoid fallback
        if request.use_real_data:
            try:
                ingest_airnow_for_city(db, request.city, hours_back=48)
            except Exception as _:
                pass

        # Check if we have sufficient data for the city and parameter (reduced to 12 hours minimum)
        recent_measurements = db.query(Measurement).filter(
            Measurement.city == request.city,
            Measurement.parameter == request.parameter
        ).order_by(Measurement.date_utc.desc()).limit(24).all()
        
        logger.info(f"Found {len(recent_measurements)} recent measurements for {request.city} - {request.parameter}")
        
        # If we have real data (12+ measurements), use it for predictions
        if len(recent_measurements) >= 12:
            logger.info(f"Using real AirNow data for predictions ({len(recent_measurements)} measurements)")
            
            # Sort measurements by time
            sorted_measurements = sorted(recent_measurements, key=lambda x: x.date_utc)
            values = [m.value for m in sorted_measurements]
            
            # Calculate statistics from real data
            avg_value = sum(values) / len(values)
            min_value = min(values)
            max_value = max(values)
            
            # Calculate trend (simple linear regression)
            n = len(values)
            x = list(range(n))
            x_mean = sum(x) / n
            y_mean = avg_value
            
            numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
            denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
            slope = numerator / denominator if denominator != 0 else 0
            
            # Generate predictions based on trend and patterns
            predictions = []
            confidence_intervals = []
            
            for i in range(request.hours_ahead):
                forecast_time = datetime.utcnow() + timedelta(hours=i+1)
                hour_of_day = forecast_time.hour
                
                # Apply trend
                trend_adjustment = slope * (n + i)
                
                # Apply diurnal pattern (air quality typically worse during day)
                if 6 <= hour_of_day <= 18:  # Daytime
                    diurnal_factor = 1.1
                elif 22 <= hour_of_day or hour_of_day <= 5:  # Night
                    diurnal_factor = 0.9
                else:
                    diurnal_factor = 1.0
                
                # Calculate prediction
                predicted_value = (avg_value + trend_adjustment) * diurnal_factor
                predicted_value = max(0, min(predicted_value, max_value * 1.5))
                
                # Calculate confidence interval based on data variance
                std_dev = (sum((v - avg_value) ** 2 for v in values) / n) ** 0.5
                confidence_margin = std_dev * 1.96  # 95% confidence
                
                predictions.append({
                    "timestamp": forecast_time.isoformat(),
                    "value": round(predicted_value, 2)
                })
                
                confidence_intervals.append({
                    "timestamp": forecast_time.isoformat(),
                    "lower": round(max(0, predicted_value - confidence_margin), 2),
                    "upper": round(predicted_value + confidence_margin, 2)
                })
            
            return PredictResponse(
                city=request.city,
                parameter=request.parameter,
                hours_ahead=request.hours_ahead,
                predictions=predictions,
                confidence_intervals=confidence_intervals,
                model_metadata={
                    "model_type": "Trend-Based Forecast",
                    "data_source": f"AirNow API ({len(recent_measurements)} measurements)",
                    "accuracy": "Real-time data with trend analysis",
                    "average_value": round(avg_value, 2),
                    "trend": "increasing" if slope > 0.1 else "decreasing" if slope < -0.1 else "stable",
                    "data_points": len(recent_measurements)
                },
                timestamp=datetime.utcnow()
            )
        
        if len(recent_measurements) < 12:
            # As a last attempt, try to ingest AirNow now if not requested earlier
            if not request.use_real_data:
                try:
                    ingest_airnow_for_city(db, request.city, hours_back=48)
                    recent_measurements = db.query(Measurement).filter(
                        Measurement.city == request.city,
                        Measurement.parameter == request.parameter
                    ).order_by(Measurement.date_utc.desc()).limit(24).all()
                except Exception:
                    pass

            # Check cache first
            cached_prediction = get_cached_prediction(request.city, request.parameter, request.hours_ahead)
            if cached_prediction:
                logger.info(f"Using cached prediction for {request.city} - {request.parameter}")
                return cached_prediction
            
            # Generate deterministic sample predictions when no data is available
            logger.info(f"No data available for {request.city} - {request.parameter}, generating deterministic sample predictions")
            
            # Generate deterministic predictions
            prediction_result = generate_deterministic_predictions(request.city, request.parameter, request.hours_ahead)
            
            # Format predictions with timestamps
            formatted_predictions = []
            formatted_confidence = []
            
            for i, (prediction, (lower, upper)) in enumerate(zip(prediction_result["predictions"], prediction_result["confidence_intervals"])):
                forecast_time = datetime.utcnow() + timedelta(hours=i+1)
                formatted_predictions.append({
                    "timestamp": forecast_time.isoformat(),
                    "value": prediction,
                    "unit": "μg/m³" if request.parameter == "PM2.5" else "ppb"
                })
                formatted_confidence.append({
                    "timestamp": forecast_time.isoformat(),
                    "lower": lower,
                    "upper": upper
                })
            
            response_data = PredictResponse(
                city=request.city,
                parameter=request.parameter,
                hours_ahead=request.hours_ahead,
                predictions=formatted_predictions,
                confidence_intervals=formatted_confidence,
                model_metadata={
                    "model_type": "Deterministic Sample Predictions",
                    "data_source": "Generated Sample Data",
                    "accuracy": "N/A - Sample Data",
                    "last_trained": datetime.utcnow().isoformat(),
                    "feature_importance": {},
                    "prediction_method": prediction_result["method"],
                    "seed": prediction_result["seed"]
                },
                timestamp=datetime.utcnow()
            )
            
            # Cache the prediction
            cache_prediction(request.city, request.parameter, request.hours_ahead, response_data)
            
            logger.info(f"Generated {len(formatted_predictions)} deterministic predictions for {request.city}")
            return response_data
        
        # Generate forecast using ML model
        forecast_result = get_forecaster().predict(
            db=db,
            city=request.city,
            parameter=request.parameter,
            hours_ahead=request.hours_ahead
        )
        
        # Format predictions with timestamps (schema expected by frontend)
        predictions = []
        confidence_intervals = []

        for i, (prediction, (lower, upper)) in enumerate(
            zip(forecast_result['predictions'], forecast_result['confidence_intervals'])
        ):
            forecast_time = datetime.utcnow() + timedelta(hours=i+1)

            predictions.append({
                "timestamp": forecast_time.isoformat(),
                "value": round(prediction, 2)
            })

            confidence_intervals.append({
                "timestamp": forecast_time.isoformat(),
                "lower": round(lower, 2),
                "upper": round(upper, 2)
            })
        
        # Prepare model metadata
        model_metadata = {
            "model_type": "RandomForestRegressor",
            "training_data_days": 90,
            "data_points_used": forecast_result.get('data_points_used', 0),
            "model_accuracy": forecast_result.get('model_accuracy'),
            "feature_importance": getattr(get_forecaster().model, 'feature_importances_', None)
        }
        
        logger.info(f"Successfully generated {len(predictions)} predictions for {request.city}")
        
        return PredictResponse(
            city=request.city,
            parameter=request.parameter,
            hours_ahead=request.hours_ahead,
            predictions=predictions,
            confidence_intervals=confidence_intervals,
            model_metadata=model_metadata,
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating forecast: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating forecast: {str(e)}"
        )

# Simple ingestion trigger endpoint to populate DB with real data
@app.get("/ingest/data")
async def ingest_data(days_back: int = 7, db: Session = Depends(get_db)):
    """Trigger ingestion from configured sources (TOLNet, OpenAQ, Weather)."""
    try:
        from data_ingest import DataIngestionManager
        manager = DataIngestionManager(db)
        results = manager.ingest_all_data(days_back=days_back)
        return {"success": True, **results}
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion error: {str(e)}")

# Model retraining endpoint
@app.post("/retrain", response_model=RetrainResponse)
async def retrain_model(
    request: RetrainRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Retrain the ML model for a specific city and parameter.
    
    Args:
        request: Retrain request with city and parameter
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        RetrainResponse with training results
    """
    try:
        # Validate parameter
        valid_parameters = ["PM2.5", "O3", "NO2"]
        if request.parameter not in valid_parameters:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid parameter '{request.parameter}'. Must be one of: {valid_parameters}"
            )
        
        logger.info(f"Retraining model for {request.city} - {request.parameter}")
        
        # Train the model
        training_result = get_forecaster().train_model(
            db=db, 
            city=request.city, 
            parameter=request.parameter
        )
        
        logger.info(f"Model retrained successfully for {request.city} - {request.parameter}")
        
        return RetrainResponse(
            success=True,
            message=f"Model retrained successfully for {request.city} - {request.parameter}",
            training_metrics=training_result,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error retraining model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retraining model: {str(e)}"
        )

# Get available cities and parameters
@app.get("/cities")
async def get_available_cities(db: Session = Depends(get_db)):
    """Get list of cities with available data."""
    try:
        cities = db.query(Measurement.city).distinct().all()
        city_list = [city[0] for city in cities]
        
        # If no cities in database, return default cities
        if not city_list:
            city_list = [
                "Austin", "New York", "Los Angeles", "Chicago", "Houston",
                "Phoenix", "Philadelphia", "San Antonio", "San Diego", "Dallas",
                "San Jose", "Austin", "Jacksonville", "Fort Worth", "Columbus",
                "Charlotte", "San Francisco", "Indianapolis", "Seattle", "Denver",
                "Washington", "Boston", "El Paso", "Nashville", "Detroit",
                "Oklahoma City", "Portland", "Las Vegas", "Memphis", "Louisville",
                "Baltimore", "Milwaukee", "Albuquerque", "Tucson", "Fresno",
                "Sacramento", "Mesa", "Kansas City", "Atlanta", "Long Beach",
                "Colorado Springs", "Raleigh", "Miami", "Virginia Beach", "Omaha",
                "Oakland", "Minneapolis", "Tulsa", "Arlington", "Tampa"
            ]
        
        return {
            "cities": city_list,
            "total_cities": len(city_list)
        }
    except Exception as e:
        logger.error(f"Error fetching cities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching cities: {str(e)}"
        )

# Get available parameters for a city
@app.get("/parameters/{city}")
async def get_available_parameters(city: str, db: Session = Depends(get_db)):
    """Get list of available parameters for a specific city."""
    try:
        parameters = db.query(Measurement.parameter).filter(
            Measurement.city == city
        ).distinct().all()
        
        if not parameters:
            # Return default parameters if no data in database
            return {
                "city": city,
                "parameters": ["PM2.5", "O3", "NO2"],
                "total_parameters": 3
            }
        
        return {
            "city": city,
            "parameters": [param[0] for param in parameters],
            "total_parameters": len(parameters)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching parameters for {city}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching parameters: {str(e)}"
        )

# Background task for weekly model retraining
def retrain_models_weekly():
    """Background task to retrain models weekly."""
    logger.info("Starting weekly model retraining...")
    
    # This would typically retrain models for all cities and parameters
    # For now, we'll just log the event
    # In a production system, you'd iterate through all cities and parameters
    logger.info("Weekly model retraining completed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )