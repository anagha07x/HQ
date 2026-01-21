"""ROI curve calculation and analysis."""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from scipy.optimize import curve_fit
from sklearn.metrics import r2_score


class ROICurve:
    """Calculate and analyze ROI curves."""
    
    def __init__(self):
        """Initialize ROI curve analyzer."""
        self.best_model = None
        self.best_params = None
        self.model_type = None
    
    def exponential_model(self, spend: np.ndarray, a: float, b: float) -> np.ndarray:
        """Exponential diminishing returns: revenue = a * (1 - exp(-b * spend)).
        
        Args:
            spend: Spend values
            a: Saturation level parameter
            b: Rate parameter
            
        Returns:
            Predicted revenue
        """
        return a * (1 - np.exp(-b * spend))
    
    def logarithmic_model(self, spend: np.ndarray, a: float, b: float) -> np.ndarray:
        """Logarithmic model: revenue = a * log(spend + 1) + b.
        
        Args:
            spend: Spend values
            a: Scale parameter
            b: Offset parameter
            
        Returns:
            Predicted revenue
        """
        return a * np.log(spend + 1) + b
    
    def fit_roi_models(self, df: pd.DataFrame, spend_col: str, revenue_col: str) -> Dict[str, any]:
        """Fit both models and select the best one.
        
        Args:
            df: Historical data
            spend_col: Spend column name
            revenue_col: Revenue column name
            
        Returns:
            Dict with best model results
        """
        spend = df[spend_col].values
        revenue = df[revenue_col].values
        
        # Fit exponential model
        try:
            exp_params, _ = curve_fit(
                self.exponential_model, 
                spend, 
                revenue,
                p0=[revenue.max(), 0.001],
                maxfev=10000
            )
            exp_pred = self.exponential_model(spend, *exp_params)
            exp_r2 = r2_score(revenue, exp_pred)
        except:
            exp_r2 = -np.inf
            exp_params = [0, 0]
        
        # Fit logarithmic model
        try:
            log_params, _ = curve_fit(
                self.logarithmic_model,
                spend,
                revenue,
                p0=[1000, 0],
                maxfev=10000
            )
            log_pred = self.logarithmic_model(spend, *log_params)
            log_r2 = r2_score(revenue, log_pred)
        except:
            log_r2 = -np.inf
            log_params = [0, 0]
        
        # Select best model
        if exp_r2 > log_r2:
            self.model_type = "exponential"
            self.best_params = exp_params
            best_r2 = exp_r2
            predictions = exp_pred
        else:
            self.model_type = "logarithmic"
            self.best_params = log_params
            best_r2 = log_r2
            predictions = log_pred
        
        # Calculate saturation and optimal spend
        saturation_spend = self._calculate_saturation_spend(spend)
        optimal_spend = self._calculate_optimal_spend(spend)
        
        # Generate ROI curve
        roi_curve = self._generate_roi_curve(spend.min(), spend.max() * 1.5)
        
        return {
            "model": "roi_curve",
            "best_fit": self.model_type,
            "parameters": {
                "a": float(self.best_params[0]),
                "b": float(self.best_params[1])
            },
            "r2_score": float(best_r2),
            "saturation_spend": float(saturation_spend),
            "optimal_spend": float(optimal_spend),
            "roi_curve": roi_curve,
            "predictions": predictions.tolist(),
            "actuals": revenue.tolist()
        }
    
    def _calculate_saturation_spend(self, spend: np.ndarray) -> float:
        """Calculate spend at which ROI saturates (95% of max revenue).
        
        Args:
            spend: Historical spend values
            
        Returns:
            Saturation spend level
        """
        if self.model_type == "exponential":
            a, b = self.best_params
            # At saturation, revenue = 0.95 * a
            # 0.95 * a = a * (1 - exp(-b * spend))
            # 0.95 = 1 - exp(-b * spend)
            # exp(-b * spend) = 0.05
            # -b * spend = ln(0.05)
            # spend = -ln(0.05) / b
            if b > 0:
                saturation = -np.log(0.05) / b
            else:
                saturation = spend.max() * 2
        else:
            # For logarithmic, use 2x max historical spend as proxy
            saturation = spend.max() * 2
        
        return saturation
    
    def _calculate_optimal_spend(self, spend: np.ndarray) -> float:
        """Calculate optimal spend (highest marginal ROI above threshold).
        
        Args:
            spend: Historical spend values
            
        Returns:
            Optimal spend level
        """
        # Generate range of spend values
        spend_range = np.linspace(spend.min(), spend.max() * 1.5, 100)
        marginal_roi = self._calculate_marginal_roi(spend_range)
        
        # Find spend where marginal ROI is still > 2.0 (good efficiency)
        good_roi_mask = marginal_roi > 2.0
        if good_roi_mask.any():
            optimal_idx = np.where(good_roi_mask)[0][-1]
            optimal = spend_range[optimal_idx]
        else:
            # If no good ROI, use median of historical spend
            optimal = np.median(spend)
        
        return optimal
    
    def _calculate_marginal_roi(self, spend: np.ndarray) -> np.ndarray:
        """Calculate marginal ROI (derivative of revenue w.r.t. spend).
        
        Args:
            spend: Spend values
            
        Returns:
            Marginal ROI values
        """
        if self.model_type == "exponential":
            a, b = self.best_params
            # d/dspend [a * (1 - exp(-b * spend))] = a * b * exp(-b * spend)
            marginal_roi = a * b * np.exp(-b * spend)
        else:
            a, b = self.best_params
            # d/dspend [a * log(spend + 1) + b] = a / (spend + 1)
            marginal_roi = a / (spend + 1)
        
        return marginal_roi
    
    def _generate_roi_curve(self, min_spend: float, max_spend: float, points: int = 20) -> List[Dict]:
        """Generate ROI curve data points.
        
        Args:
            min_spend: Minimum spend value
            max_spend: Maximum spend value
            points: Number of points to generate
            
        Returns:
            List of {spend, roi} dictionaries
        """
        spend_range = np.linspace(min_spend, max_spend, points)
        marginal_roi = self._calculate_marginal_roi(spend_range)
        
        roi_curve = [
            {
                "spend": float(s),
                "marginal_roi": float(r)
            }
            for s, r in zip(spend_range, marginal_roi)
        ]
        
        return roi_curve
    
    def calculate_roi(self, investment: float, returns: pd.Series) -> pd.Series:
        """Calculate ROI over time.
        
        Args:
            investment: Initial investment
            returns: Time series of returns
            
        Returns:
            ROI time series
        """
        roi = (returns - investment) / investment * 100
        return roi
    
    def calculate_cumulative_roi(self, roi_series: pd.Series) -> pd.Series:
        """Calculate cumulative ROI.
        
        Args:
            roi_series: ROI time series
            
        Returns:
            Cumulative ROI series
        """
        cumulative = (1 + roi_series / 100).cumprod() - 1
        return cumulative * 100
    
    def find_breakeven_point(self, roi_series: pd.Series) -> Tuple[int, float]:
        """Find breakeven point.
        
        Args:
            roi_series: ROI time series
            
        Returns:
            Tuple of (period, ROI value)
        """
        positive_roi = roi_series > 0
        if positive_roi.any():
            breakeven_idx = positive_roi.idxmax()
            return int(breakeven_idx), float(roi_series.iloc[breakeven_idx])
        return -1, 0.0
    
    def project_roi(self, historical_roi: pd.Series, horizon: int) -> pd.Series:
        """Project future ROI.
        
        Args:
            historical_roi: Historical ROI data
            horizon: Projection horizon
            
        Returns:
            Projected ROI series
        """
        # Simple projection: use mean of last 3 periods
        recent_mean = historical_roi.tail(3).mean()
        projected = pd.Series([recent_mean] * horizon)
        return projected
