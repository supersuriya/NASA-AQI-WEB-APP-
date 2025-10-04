"""
Pydantic schemas for request/response validation in AirSense API.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

class ParameterType(str, Enum):
    """Enum for air quality parameters."""
    PM25 = "PM2.5"
    O3 = "O3"
    NO2 = "NO2"

class SourceType(str, Enum):
    """Enum for data sources."""
    OPENAQ = "openaq"
    TEMPO = "tempo"

class MeasurementBase(BaseModel):
    """Base schema for measurement data."""
    city: str = Field(..., min_length=1, max_length=100, description="City name")
    parameter: ParameterType = Field(..., description="Air quality parameter")
    value: float = Field(..., ge=0, description="Measurement value")
    unit: str = Field(..., min_length=1, max_length=10, description="Unit of measurement")
    date_utc: datetime = Field(..., description="UTC timestamp of measurement")
    source: SourceType = Field(default=SourceType.OPENAQ, description="Data source")

class MeasurementCreate(MeasurementBase):
    """Schema for creating a new measurement."""
    pass

class MeasurementResponse(MeasurementBase):
    """Schema for measurement response."""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ForecastRequest(BaseModel):
    """Schema for forecast request."""
    city: str = Field(..., min_length=1, max_length=100, description="City name for forecast")
    parameter: ParameterType = Field(default=ParameterType.PM25, description="Parameter to forecast")
    hours_ahead: int = Field(default=24, ge=1, le=168, description="Hours ahead to forecast (1-168)")

class ForecastResponse(BaseModel):
    """Schema for forecast response."""
    city: str
    parameter: str
    forecast_date: datetime
    predicted_value: float
    confidence_interval_lower: Optional[float] = None
    confidence_interval_upper: Optional[float] = None
    model_accuracy: Optional[float] = None
    data_points_used: int
    
    class Config:
        from_attributes = True

class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str = Field(default="ok", description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Current UTC timestamp")
    version: str = Field(default="1.0.0", description="API version")

class IngestResponse(BaseModel):
    """Schema for data ingestion response."""
    success: bool
    message: str
    records_processed: int
    source: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ErrorResponse(BaseModel):
    """Schema for error responses."""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class OpenAQData(BaseModel):
    """Schema for OpenAQ API response data."""
    results: List[Dict[str, Any]]

class TEMPOData(BaseModel):
    """Schema for NASA TEMPO data."""
    files: List[str]
    download_path: str
    records_processed: int
