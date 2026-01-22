"""Dataset registry for managing uploaded datasets."""

from typing import Dict, Any
from dataclasses import dataclass
import pandas as pd


@dataclass
class DatasetRegistry:
    """Registry object for uploaded datasets.
    
    Attributes:
        dataset_id: Unique identifier for the dataset
        source_type: Type of source file (csv, xlsx, json)
        datasets: Dictionary mapping dataset names to DataFrames
        metadata: Additional metadata about the datasets
    """
    dataset_id: str
    source_type: str
    datasets: Dict[str, pd.DataFrame]
    metadata: Dict[str, Any]
    
    def get_primary_dataset(self) -> pd.DataFrame:
        """Get the primary/first dataset.
        
        Returns:
            Primary DataFrame
        """
        if not self.datasets:
            raise ValueError("No datasets available")
        
        # For single-sheet files, return the only dataset
        if len(self.datasets) == 1:
            return list(self.datasets.values())[0]
        
        # For multi-sheet files, return the first sheet
        first_key = list(self.datasets.keys())[0]
        return self.datasets[first_key]
    
    def get_dataset(self, name: str) -> pd.DataFrame:
        """Get a specific dataset by name.
        
        Args:
            name: Name of the dataset
            
        Returns:
            DataFrame for the specified dataset
            
        Raises:
            KeyError: If dataset name not found
        """
        if name not in self.datasets:
            raise KeyError(f"Dataset '{name}' not found. Available: {list(self.datasets.keys())}")
        return self.datasets[name]
    
    def list_datasets(self) -> list:
        """List all available dataset names.
        
        Returns:
            List of dataset names
        """
        return list(self.datasets.keys())
