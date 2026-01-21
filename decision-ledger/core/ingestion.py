"""Data ingestion module for CSV files."""

import pandas as pd
from typing import Optional, Dict, Any
import os


class DataIngestion:
    """Handle data ingestion from CSV files."""
    
    def __init__(self):
        """Initialize data ingestion."""
        pass
    
    async def ingest_csv(self, file_path: str) -> pd.DataFrame:
        """Ingest CSV file and return DataFrame.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            pd.DataFrame: Loaded data
        """
        try:
            # Try different encodings
            df = pd.read_csv(file_path)
            return df
        except UnicodeDecodeError:
            # Try with different encoding
            df = pd.read_csv(file_path, encoding='latin-1')
            return df
    
    def validate_file(self, file_path: str) -> bool:
        """Validate file format and size.
        
        Args:
            file_path: Path to file
            
        Returns:
            bool: True if valid
        """
        if not os.path.exists(file_path):
            return False
        
        if not file_path.endswith('.csv'):
            return False
        
        # Check file size (max 10MB)
        file_size = os.path.getsize(file_path)
        max_size = 10 * 1024 * 1024  # 10MB
        
        return file_size <= max_size
    
    def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract file metadata.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dict containing metadata
        """
        return {
            "filename": os.path.basename(file_path),
            "size_bytes": os.path.getsize(file_path),
            "path": file_path
        }
