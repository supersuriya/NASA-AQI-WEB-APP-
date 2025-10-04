"""
SQLAlchemy ORM models for AirSense application.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from sqlalchemy.sql import func
from database import Base

class Measurement(Base):
    """
    Model for storing air quality measurements from OpenAQ and NASA TEMPO.
    """
    __tablename__ = "measurements"
    
    id = Column(Integer, primary_key=True, index=True)
    city = Column(String(100), nullable=False, index=True)
    parameter = Column(String(20), nullable=False, index=True)  # PM2.5, O3, NO2
    value = Column(Float, nullable=False)
    unit = Column(String(10), nullable=False)  # µg/m³, ppm, etc.
    date_utc = Column(DateTime, nullable=False, index=True)
    source = Column(String(20), nullable=False, default="openaq")  # openaq, tempo
    created_at = Column(DateTime, default=func.now())
    
    # Create composite index for efficient queries
    __table_args__ = (
        Index('idx_city_param_date', 'city', 'parameter', 'date_utc'),
        Index('idx_source_param', 'source', 'parameter'),
    )
    
    def __repr__(self):
        return f"<Measurement(city='{self.city}', parameter='{self.parameter}', value={self.value}, date_utc='{self.date_utc}')>"

class Forecast(Base):
    """
    Model for storing air quality forecasts.
    """
    __tablename__ = "forecasts"
    
    id = Column(Integer, primary_key=True, index=True)
    city = Column(String(100), nullable=False, index=True)
    parameter = Column(String(20), nullable=False, index=True)
    predicted_value = Column(Float, nullable=False)
    confidence_interval_lower = Column(Float, nullable=True)
    confidence_interval_upper = Column(Float, nullable=True)
    forecast_date = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now())
    
    def __repr__(self):
        return f"<Forecast(city='{self.city}', parameter='{self.parameter}', predicted_value={self.predicted_value}, forecast_date='{self.forecast_date}')>"
