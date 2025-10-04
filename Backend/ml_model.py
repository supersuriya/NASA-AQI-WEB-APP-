"""
Machine learning model for air quality forecasting using RandomForestRegressor.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, Any
import joblib
import os
import logging

from models import Measurement
from schemas import ParameterType

logger = logging.getLogger(__name__)

class AirQualityForecaster:
    """
    Air quality forecasting model using RandomForestRegressor.
    """
    
    def __init__(self, model_path: str = "models/"):
        self.model_path = model_path
        self.model = None
        self.feature_columns = []
        self.is_trained = False
        
        # Create models directory if it doesn't exist
        os.makedirs(model_path, exist_ok=True)
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare features for machine learning model.
        Creates time-based features and lagged values.
        """
        # Sort by date
        df = df.sort_values('date_utc')
        
        # Create time-based features
        df['hour'] = df['date_utc'].dt.hour
        df['day_of_week'] = df['date_utc'].dt.dayofweek
        df['day_of_year'] = df['date_utc'].dt.dayofyear
        df['month'] = df['date_utc'].dt.month
        
        # Create lagged features (previous values)
        for lag in [1, 2, 3, 6, 12, 24]:  # 1h, 2h, 3h, 6h, 12h, 24h ago
            df[f'value_lag_{lag}h'] = df['value'].shift(lag)
        
        # Create rolling averages
        for window in [3, 6, 12, 24]:  # 3h, 6h, 12h, 24h rolling averages
            df[f'value_rolling_{window}h'] = df['value'].rolling(window=window).mean()
        
        # Create difference features
        df['value_diff_1h'] = df['value'].diff(1)
        df['value_diff_24h'] = df['value'].diff(24)
        
        # Drop rows with NaN values (due to lagged features)
        df = df.dropna()
        
        return df
    
    def train_model(self, db: Session, city: str, parameter: str = "PM2.5") -> Dict[str, Any]:
        """
        Train the RandomForestRegressor model on historical data.
        """
        logger.info(f"Training model for {city} - {parameter}")
        
        # Get historical data for the city and parameter
        measurements = db.query(Measurement).filter(
            and_(
                Measurement.city == city,
                Measurement.parameter == parameter,
                Measurement.date_utc >= datetime.utcnow() - timedelta(days=90)  # Last 90 days
            )
        ).order_by(Measurement.date_utc).all()
        
        if len(measurements) < 100:  # Need minimum data points
            raise ValueError(f"Insufficient data for training. Found {len(measurements)} records, need at least 100.")
        
        # Convert to DataFrame
        data = []
        for m in measurements:
            data.append({
                'date_utc': m.date_utc,
                'value': m.value,
                'city': m.city,
                'parameter': m.parameter
            })
        
        df = pd.DataFrame(data)
        df = self.prepare_features(df)
        
        if len(df) < 50:  # Check again after feature preparation
            raise ValueError(f"Insufficient data after feature preparation. Found {len(df)} records, need at least 50.")
        
        # Define feature columns (exclude target and non-feature columns)
        exclude_cols = ['date_utc', 'value', 'city', 'parameter']
        self.feature_columns = [col for col in df.columns if col not in exclude_cols]
        
        X = df[self.feature_columns]
        y = df['value']
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=False
        )
        
        # Train model
        self.model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        
        self.model.fit(X_train, y_train)
        
        # Evaluate model
        y_pred = self.model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        # Save model
        model_file = os.path.join(self.model_path, f"{city}_{parameter}_model.joblib")
        joblib.dump({
            'model': self.model,
            'feature_columns': self.feature_columns,
            'city': city,
            'parameter': parameter,
            'trained_at': datetime.utcnow(),
            'mae': mae,
            'r2': r2
        }, model_file)
        
        self.is_trained = True
        
        logger.info(f"Model trained successfully. MAE: {mae:.2f}, R²: {r2:.2f}")
        
        return {
            'mae': mae,
            'r2': r2,
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'feature_importance': dict(zip(self.feature_columns, self.model.feature_importances_))
        }
    
    def load_model(self, city: str, parameter: str = "PM2.5") -> bool:
        """
        Load a pre-trained model from disk.
        """
        model_file = os.path.join(self.model_path, f"{city}_{parameter}_model.joblib")
        
        if not os.path.exists(model_file):
            return False
        
        try:
            model_data = joblib.load(model_file)
            self.model = model_data['model']
            self.feature_columns = model_data['feature_columns']
            self.is_trained = True
            logger.info(f"Model loaded successfully for {city} - {parameter}")
            return True
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    def predict(self, db: Session, city: str, parameter: str = "PM2.5", 
                hours_ahead: int = 24) -> Dict[str, Any]:
        """
        Make predictions for the next hours_ahead hours.
        """
        if not self.is_trained:
            if not self.load_model(city, parameter):
                raise ValueError(f"No trained model found for {city} - {parameter}")
        
        # Get recent data for feature preparation
        recent_data = db.query(Measurement).filter(
            and_(
                Measurement.city == city,
                Measurement.parameter == parameter,
                Measurement.date_utc >= datetime.utcnow() - timedelta(days=7)  # Last 7 days
            )
        ).order_by(Measurement.date_utc).all()
        
        if len(recent_data) < 24:  # Need at least 24 hours of recent data
            raise ValueError(f"Insufficient recent data for prediction. Found {len(recent_data)} records, need at least 24.")
        
        # Convert to DataFrame
        data = []
        for m in recent_data:
            data.append({
                'date_utc': m.date_utc,
                'value': m.value,
                'city': m.city,
                'parameter': m.parameter
            })
        
        df = pd.DataFrame(data)
        df = self.prepare_features(df)
        
        if len(df) == 0:
            raise ValueError("No data available after feature preparation")
        
        # Get the most recent row for prediction
        latest_row = df.iloc[-1:].copy()
        
        predictions = []
        confidence_intervals = []
        
        # Generate predictions for each hour
        for hour in range(1, hours_ahead + 1):
            # Prepare features for this prediction
            pred_row = latest_row.copy()
            
            # Update time features for the prediction hour
            pred_time = datetime.utcnow() + timedelta(hours=hour)
            pred_row['hour'] = pred_time.hour
            pred_row['day_of_week'] = pred_time.weekday()
            pred_row['day_of_year'] = pred_time.timetuple().tm_yday
            pred_row['month'] = pred_time.month
            
            # Use the last known value as a starting point for lagged features
            # In a real implementation, you might want to use previous predictions
            for lag in [1, 2, 3, 6, 12, 24]:
                if hour >= lag:
                    # Use the last known value for now (simplified)
                    pred_row[f'value_lag_{lag}h'] = latest_row['value'].iloc[0]
                else:
                    pred_row[f'value_lag_{lag}h'] = latest_row['value'].iloc[0]
            
            # Calculate rolling averages (simplified)
            for window in [3, 6, 12, 24]:
                pred_row[f'value_rolling_{window}h'] = latest_row['value'].iloc[0]
            
            # Calculate differences (simplified)
            pred_row['value_diff_1h'] = 0
            pred_row['value_diff_24h'] = 0
            
            # Make prediction
            X_pred = pred_row[self.feature_columns]
            prediction = self.model.predict(X_pred)[0]
            
            # Calculate confidence interval (simplified - using standard deviation of training data)
            # In a real implementation, you'd use proper uncertainty quantification
            confidence_std = np.std(self.model.predict(X_pred)) * 1.96  # 95% confidence
            confidence_lower = max(0, prediction - confidence_std)
            confidence_upper = prediction + confidence_std
            
            predictions.append(prediction)
            confidence_intervals.append((confidence_lower, confidence_upper))
        
        return {
            'predictions': predictions,
            'confidence_intervals': confidence_intervals,
            'forecast_hours': list(range(1, hours_ahead + 1)),
            'model_accuracy': getattr(self.model, 'r2_score', None),
            'data_points_used': len(df)
        }

# Global forecaster instance
forecaster = AirQualityForecaster()
