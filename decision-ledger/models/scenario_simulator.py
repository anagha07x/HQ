"""Scenario simulation and what-if analysis."""

import pandas as pd
import numpy as np
from typing import Dict, List, Any


class ScenarioSimulator:
    """Simulate different decision scenarios."""
    
    def __init__(self):
        """Initialize scenario simulator."""
        self.scenarios = {}
        self.roi_model = None
        self.roi_model_type = None
        self.roi_params = None
    
    def set_roi_model(self, model_type: str, parameters: Dict[str, float]):
        """Set ROI model for simulations.
        
        Args:
            model_type: "exponential" or "logarithmic"
            parameters: Model parameters (a, b)
        """
        self.roi_model_type = model_type
        self.roi_params = parameters
    
    def predict_revenue(self, spend: float) -> float:
        """Predict revenue for given spend using ROI model.
        
        Args:
            spend: Spend amount
            
        Returns:
            Predicted revenue
        """
        if self.roi_model_type is None:
            raise ValueError("ROI model not set. Call set_roi_model first.")
        
        a = self.roi_params["a"]
        b = self.roi_params["b"]
        
        if self.roi_model_type == "exponential":
            revenue = a * (1 - np.exp(-b * spend))
        else:  # logarithmic
            revenue = a * np.log(spend + 1) + b
        
        return float(revenue)
    
    def calculate_marginal_roi(self, spend: float) -> float:
        """Calculate marginal ROI at given spend level.
        
        Args:
            spend: Spend amount
            
        Returns:
            Marginal ROI
        """
        if self.roi_model_type is None:
            raise ValueError("ROI model not set. Call set_roi_model first.")
        
        a = self.roi_params["a"]
        b = self.roi_params["b"]
        
        if self.roi_model_type == "exponential":
            marginal_roi = a * b * np.exp(-b * spend)
        else:  # logarithmic
            marginal_roi = a / (spend + 1)
        
        return float(marginal_roi)
    
    def simulate_what_if(self, current_spend: float, proposed_spend: float) -> Dict[str, Any]:
        """Simulate what-if scenario comparing two spend levels.
        
        Args:
            current_spend: Current spend amount
            proposed_spend: Proposed spend amount
            
        Returns:
            Simulation results with comparison and recommendation
        """
        # Predict revenues
        current_revenue = self.predict_revenue(current_spend)
        proposed_revenue = self.predict_revenue(proposed_spend)
        
        # Calculate marginal ROIs
        current_marginal_roi = self.calculate_marginal_roi(current_spend)
        proposed_marginal_roi = self.calculate_marginal_roi(proposed_spend)
        
        # Calculate deltas
        delta_spend = proposed_spend - current_spend
        delta_revenue = proposed_revenue - current_revenue
        
        # Calculate incremental ROI (return on the additional spend)
        if delta_spend != 0:
            incremental_roi = delta_revenue / abs(delta_spend)
        else:
            incremental_roi = 0
        
        # Determine efficiency change
        if proposed_marginal_roi > current_marginal_roi:
            efficiency_change = "increase"
        elif proposed_marginal_roi < current_marginal_roi:
            efficiency_change = "decrease"
        else:
            efficiency_change = "neutral"
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            delta_spend, 
            incremental_roi, 
            proposed_marginal_roi,
            efficiency_change
        )
        
        return {
            "current": {
                "spend": float(current_spend),
                "estimated_revenue": float(current_revenue),
                "marginal_roi": float(current_marginal_roi)
            },
            "proposed": {
                "spend": float(proposed_spend),
                "estimated_revenue": float(proposed_revenue),
                "marginal_roi": float(proposed_marginal_roi)
            },
            "impact": {
                "delta_spend": float(delta_spend),
                "delta_revenue": float(delta_revenue),
                "incremental_roi": float(incremental_roi),
                "efficiency_change": efficiency_change
            },
            "recommendation": recommendation
        }
    
    def _generate_recommendation(self, delta_spend: float, incremental_roi: float, 
                                 proposed_marginal_roi: float, efficiency_change: str) -> str:
        """Generate recommendation based on simulation results.
        
        Args:
            delta_spend: Change in spend
            incremental_roi: ROI on additional spend
            proposed_marginal_roi: Marginal ROI at proposed level
            efficiency_change: Direction of efficiency change
            
        Returns:
            Recommendation: "scale", "hold", or "reduce"
        """
        if delta_spend > 0:
            # Increasing spend
            if incremental_roi > 2.0 and proposed_marginal_roi > 2.0:
                return "scale"
            elif incremental_roi > 1.5:
                return "scale"
            elif incremental_roi > 1.0:
                return "hold"
            else:
                return "hold"
        elif delta_spend < 0:
            # Reducing spend
            if proposed_marginal_roi > 3.0:
                return "hold"
            elif proposed_marginal_roi < 2.0:
                return "reduce"
            else:
                return "hold"
        else:
            return "hold"
    
    def create_scenario(self, name: str, parameters: Dict[str, Any]) -> None:
        """Create a new scenario.
        
        Args:
            name: Scenario name
            parameters: Scenario parameters
        """
        self.scenarios[name] = parameters
    
    def simulate_scenario(self, scenario_name: str, base_forecast: pd.DataFrame) -> pd.DataFrame:
        """Simulate a scenario.
        
        Args:
            scenario_name: Name of scenario to simulate
            base_forecast: Base forecast data
            
        Returns:
            Simulated forecast DataFrame
        """
        # Placeholder for future implementation
        return base_forecast.copy()
    
    def compare_scenarios(self, scenario_names: List[str]) -> pd.DataFrame:
        """Compare multiple scenarios.
        
        Args:
            scenario_names: List of scenario names
            
        Returns:
            Comparison DataFrame
        """
        # Placeholder for future implementation
        return pd.DataFrame()
    
    def monte_carlo_simulation(self, base_forecast: pd.DataFrame, n_simulations: int = 1000) -> Dict[str, Any]:
        """Run Monte Carlo simulation.
        
        Args:
            base_forecast: Base forecast
            n_simulations: Number of simulations
            
        Returns:
            Simulation results
        """
        # Placeholder for future implementation
        return {
            "mean": 0,
            "std": 0,
            "confidence_interval": [0, 0]
        }
