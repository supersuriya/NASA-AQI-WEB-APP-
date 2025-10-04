"""
AirSense FastAPI Application - Air Quality Forecasting System
Integrates NASA TEMPO, Pandora, TOLNet, and AirNow data for North American cities.
"""
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from database import get_db, create_tables
from models import Measurement, Forecast
from schemas import (
    ForecastRequest, ForecastResponse, HealthResponse, IngestResponse,
    ErrorResponse, MeasurementResponse, ParameterType
)
from ml_model import forecaster
from utils.nasa_data_client import NASADataClient
from utils.data_processor import DataProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables for clients
nasa_client = None
scheduler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    global nasa_client, scheduler
    
    # Startup
    logger.info("Starting AirSense application...")
    
    # Create database tables
    create_tables()
    logger.info("Database tables created")
    
    # Initialize NASA data client
    try:
        nasa_client = NASADataClient()
        logger.info("NASA data client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize NASA data client: {e}")
    
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
    logger.info("Background scheduler started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AirSense application...")
    if scheduler:
        scheduler.shutdown()
    logger.info("Application shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="AirSense API",
    description="Air Quality Forecasting System integrating OpenAQ and NASA TEMPO data",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        timestamp=datetime.utcnow(),
        version="1.0.0"
    )

# NASA data ingestion endpoint
@app.post("/ingest/nasa", response_model=IngestResponse)
async def ingest_nasa_data(
    city: str,
    parameters: List[str] = None,
    days_back: int = 7,
    sources: List[str] = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Ingest air quality data from NASA sources (TEMPO, Pandora, TOLNet, AirNow).
    
    Args:
        city: City name to fetch data for
        parameters: List of parameters (NO2, O3, HCHO, PM2.5)
        days_back: Number of days to look back
        sources: List of NASA data sources to use
        background_tasks: FastAPI background tasks
        db: Database session
    """
    if not nasa_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NASA data client not available"
        )
    
    if parameters is None:
        parameters = ["NO2", "O3", "HCHO", "PM2.5"]
    
    if sources is None:
        sources = ["tempo", "pandora", "tolnet", "airnow"]
    
    try:
        logger.info(f"Ingesting NASA data for {city}")
        
        # Fetch data from NASA sources
        nasa_data = nasa_client.get_air_quality_data(
            city=city,
            parameters=parameters,
            days_back=days_back,
            sources=sources
        )
        
        all_measurements = nasa_data.get('all_measurements', [])
        
        if not all_measurements:
            return IngestResponse(
                success=False,
                message=f"No NASA data found for {city}",
                records_processed=0,
                source="nasa"
            )
        
        # Clean and validate data
        cleaned_measurements = DataProcessor.clean_measurements(all_measurements)
        
        if not cleaned_measurements:
            return IngestResponse(
                success=False,
                message=f"No valid NASA data found for {city} after cleaning",
                records_processed=0,
                source="nasa"
            )
        
        # Store in database
        records_processed = 0
        for measurement_data in cleaned_measurements:
            try:
                measurement = Measurement(**measurement_data)
                db.add(measurement)
                records_processed += 1
            except Exception as e:
                logger.error(f"Error storing measurement: {e}")
                continue
        
        db.commit()
        
        logger.info(f"Successfully ingested {records_processed} NASA records for {city}")
        
        return IngestResponse(
            success=True,
            message=f"Successfully ingested {records_processed} NASA records for {city}",
            records_processed=records_processed,
            source="nasa"
        )
        
    except Exception as e:
        logger.error(f"Error ingesting NASA data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error ingesting NASA data: {str(e)}"
        )


# Forecast endpoint
@app.post("/forecast", response_model=List[ForecastResponse])
async def forecast_air_quality(
    request: ForecastRequest,
    db: Session = Depends(get_db)
):
    """
    Generate air quality forecast for a city.
    
    Args:
        request: Forecast request containing city and parameters
        db: Database session
    """
    try:
        logger.info(f"Generating forecast for {request.city} - {request.parameter}")
        
        # Generate forecast using ML model
        forecast_result = forecaster.predict(
            db=db,
            city=request.city,
            parameter=request.parameter,
            hours_ahead=request.hours_ahead
        )
        
        # Create forecast responses
        forecasts = []
        for i, (prediction, (lower, upper)) in enumerate(
            zip(forecast_result['predictions'], forecast_result['confidence_intervals'])
        ):
            forecast_date = datetime.utcnow() + timedelta(hours=i+1)
            
            # Store forecast in database
            forecast_record = Forecast(
                city=request.city,
                parameter=request.parameter,
                predicted_value=prediction,
                confidence_interval_lower=lower,
                confidence_interval_upper=upper,
                forecast_date=forecast_date
            )
            db.add(forecast_record)
            
            # Create response
            forecast_response = ForecastResponse(
                city=request.city,
                parameter=request.parameter,
                forecast_date=forecast_date,
                predicted_value=prediction,
                confidence_interval_lower=lower,
                confidence_interval_upper=upper,
                model_accuracy=forecast_result.get('model_accuracy'),
                data_points_used=forecast_result.get('data_points_used', 0)
            )
            forecasts.append(forecast_response)
        
        db.commit()
        
        logger.info(f"Generated {len(forecasts)} forecast points for {request.city}")
        return forecasts
        
    except Exception as e:
        logger.error(f"Error generating forecast: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating forecast: {str(e)}"
        )

# Get recent measurements endpoint
@app.get("/measurements", response_model=List[MeasurementResponse])
async def get_measurements(
    city: str = None,
    parameter: str = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get recent air quality measurements.
    
    Args:
        city: Filter by city name
        parameter: Filter by parameter (PM2.5, O3, NO2)
        limit: Maximum number of records to return
        db: Database session
    """
    try:
        query = db.query(Measurement)
        
        if city:
            query = query.filter(Measurement.city == city)
        if parameter:
            query = query.filter(Measurement.parameter == parameter)
        
        measurements = query.order_by(Measurement.date_utc.desc()).limit(limit).all()
        
        return measurements
        
    except Exception as e:
        logger.error(f"Error fetching measurements: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching measurements: {str(e)}"
        )

# Train model endpoint
@app.post("/train-model")
async def train_model(
    city: str,
    parameter: str = "PM2.5",
    db: Session = Depends(get_db)
):
    """
    Train the ML model for a specific city and parameter.
    
    Args:
        city: City name
        parameter: Parameter to train for
        db: Database session
    """
    try:
        logger.info(f"Training model for {city} - {parameter}")
        
        # Train the model
        training_result = forecaster.train_model(db=db, city=city, parameter=parameter)
        
        return {
            "success": True,
            "message": f"Model trained successfully for {city} - {parameter}",
            "training_metrics": training_result
        }
        
    except Exception as e:
        logger.error(f"Error training model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error training model: {str(e)}"
        )

# Background task for weekly model retraining
def retrain_models_weekly():
    """Background task to retrain models weekly."""
    logger.info("Starting weekly model retraining...")
    
    # This would typically retrain models for all cities
    # For now, we'll just log the event
    logger.info("Weekly model retraining completed")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "AirSense API - Air Quality Forecasting System",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "ingest_nasa": "/ingest/nasa",
            "forecast": "/forecast",
            "measurements": "/measurements",
            "train_model": "/train-model"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
