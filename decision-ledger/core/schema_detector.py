"""Automatic schema detection for datasets."""

import pandas as pd
from typing import Dict, Any, List, Optional
import re


class SchemaDetector:
    """Detect and infer schema from data."""
    
    def detect_schema(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect data types and schema.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Dict containing schema information
        """
        schema = {
            "columns": list(df.columns),
            "rows": len(df),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "date_column": self.detect_date_columns(df),
            "numeric_columns": self.detect_numeric_columns(df),
            "spend_column": self._detect_spend_column(df),
            "revenue_column": self._detect_revenue_column(df),
        }
        return schema
    
    def detect_date_columns(self, df: pd.DataFrame) -> Optional[str]:
        """Identify date/time columns.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Name of detected date column or None
        """
        # Look for common date column names
        date_keywords = ['date', 'time', 'datetime', 'timestamp', 'day', 'dt']
        
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in date_keywords):
                return col
        
        # Try to parse columns as dates
        for col in df.columns:
            try:
                pd.to_datetime(df[col].dropna().head(10))
                return col
            except:
                continue
        
        return None
    
    def detect_numeric_columns(self, df: pd.DataFrame) -> List[str]:
        """Identify numeric columns.
        
        Args:
            df: Input DataFrame
            
        Returns:
            List of numeric column names
        """
        return df.select_dtypes(include=['number']).columns.tolist()
    
    def detect_categorical_columns(self, df: pd.DataFrame) -> List[str]:
        """Identify categorical columns.
        
        Args:
            df: Input DataFrame
            
        Returns:
            List of categorical column names
        """
        return df.select_dtypes(include=['object', 'category']).columns.tolist()
    
    def suggest_target_column(self, df: pd.DataFrame) -> str:
        """Suggest most likely target column for forecasting.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Suggested target column name
        """
        # Look for revenue or spend first
        revenue_col = self._detect_revenue_column(df)
        if revenue_col:
            return revenue_col
        
        # Otherwise, return first numeric column
        numeric_cols = self.detect_numeric_columns(df)
        return numeric_cols[0] if numeric_cols else df.columns[0]
    
    def _detect_spend_column(self, df: pd.DataFrame) -> Optional[str]:
        """Detect spend/cost column.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Detected spend column name or None
        """
        spend_keywords = ['spend', 'cost', 'expense', 'budget', 'expenditure', 'investment']
        
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in spend_keywords):
                # Verify it's numeric
                if pd.api.types.is_numeric_dtype(df[col]):
                    return col
        
        return None
    
    def _detect_revenue_column(self, df: pd.DataFrame) -> Optional[str]:
        """Detect revenue/sales column.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Detected revenue column name or None
        """
        revenue_keywords = ['revenue', 'sales', 'income', 'earnings', 'profit', 'return']
        
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in revenue_keywords):
                # Verify it's numeric
                if pd.api.types.is_numeric_dtype(df[col]):
                    return col
        
        return None
