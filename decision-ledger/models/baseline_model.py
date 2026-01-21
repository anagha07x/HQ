"""Baseline forecasting models."""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_percentage_error


class BaselineModel:
    """Simple baseline models for comparison."""
    
    def __init__(self):
        """Initialize baseline model."""
        self.model = None
        self.predictions = None
    
    def train_spend_revenue_model(self, df: pd.DataFrame, spend_col: str, revenue_col: str) -> Dict[str, Any]:
        """Train simple linear regression: revenue = a * spend + b.
        
        Args:
            df: Historical data
            spend_col: Spend column name
            revenue_col: Revenue column name
            
        Returns:
            Dict with model results and metrics
        """
        # Prepare data
        X = df[[spend_col]].values
        y = df[revenue_col].values
        
        # Train model
        self.model = LinearRegression()
        self.model.fit(X, y)
        
        # Generate predictions
        y_pred = self.model.predict(X)
        
        # Calculate metrics
        r2 = r2_score(y, y_pred)
        mape = mean_absolute_percentage_error(y, y_pred) * 100  # Convert to percentage
        
        # Get coefficients
        coefficient = self.model.coef_[0]
        intercept = self.model.intercept_
        
        # Calculate residuals
        residuals = y - y_pred
        
        # Get latest month data
        latest_idx = len(df) - 1
        latest_spend = float(df[spend_col].iloc[latest_idx])
        latest_actual_revenue = float(df[revenue_col].iloc[latest_idx])
        latest_predicted_revenue = float(y_pred[latest_idx])
        
        return {
            "model": "baseline_regression",
            "formula": f"revenue = {coefficient:.2f} * spend + {intercept:.2f}",
            "coefficient": float(coefficient),
            "intercept": float(intercept),
            "metrics": {
                "r2": float(r2),
                "mape": float(mape)
            },
            "latest_month": {
                "spend": latest_spend,
                "actual_revenue": latest_actual_revenue,
                "predicted_revenue": latest_predicted_revenue,
                "residual": float(residuals[latest_idx])
            },
            "predictions": y_pred.tolist(),
            "actuals": y.tolist(),
            "residuals": residuals.tolist()
        }
    
    def predict_revenue(self, spend: float) -> float:
        """Predict revenue for given spend.
        
        Args:
            spend: Spend amount
            
        Returns:
            Predicted revenue
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train_spend_revenue_model first.")
        
        return float(self.model.predict([[spend]])[0])
    
    def naive_forecast(self, df: pd.DataFrame, target_col: str, horizon: int) -> pd.DataFrame:
        """Naive forecast (last value repeated).
        
        Args:
            df: Historical data
            target_col: Target column
            horizon: Forecast horizon
            
        Returns:
            Forecast DataFrame
        """
        last_value = df[target_col].iloc[-1]
        forecast = pd.DataFrame({
            target_col: [last_value] * horizon
        })
        return forecast
    
    def moving_average_forecast(self, df: pd.DataFrame, target_col: str, window: int, horizon: int) -> pd.DataFrame:
        """Moving average forecast.
        
        Args:
            df: Historical data
            target_col: Target column
            window: Moving average window
            horizon: Forecast horizon
            
        Returns:
            Forecast DataFrame
        """
        ma_value = df[target_col].tail(window).mean()
        forecast = pd.DataFrame({
            target_col: [ma_value] * horizon
        })
        return forecast
    
    def seasonal_naive_forecast(self, df: pd.DataFrame, target_col: str, period: int, horizon: int) -> pd.DataFrame:
        """Seasonal naive forecast.
        
        Args:
            df: Historical data
            target_col: Target column
            period: Seasonal period
            horizon: Forecast horizon
            
        Returns:
            Forecast DataFrame
        """
        # Get last period values
        last_period = df[target_col].tail(period).values
        
        # Repeat for horizon
        forecast_values = np.tile(last_period, (horizon // period) + 1)[:horizon]
        
        forecast = pd.DataFrame({
            target_col: forecast_values
        })
        return forecast
