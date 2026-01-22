"""Column role detection and mapping system."""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from collections import Counter


class ColumnRoleMapper:
    """Detect and map column roles for data modeling."""
    
    VALID_ROLES = ["TIME", "ACTION", "OUTCOME", "METRIC", "DIMENSION", "IGNORE"]
    
    def __init__(self):
        """Initialize role mapper."""
        self.column_roles = {}
    
    def detect_roles(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect roles for all columns with confidence scores.
        
        Args:
            df: Input DataFrame
            
        Returns:
            List of column role assignments with confidence
        """
        results = []
        
        for col in df.columns:
            role, confidence = self._detect_column_role(df, col)
            
            # Get sample values, converting NaN/inf to None for JSON safety
            sample_values = []
            for val in df[col].head(3).tolist():
                if pd.isna(val) or (isinstance(val, float) and (np.isinf(val) or np.isnan(val))):
                    sample_values.append(None)
                else:
                    sample_values.append(val)
            
            results.append({
                "name": col,
                "detected_role": role,
                "confidence": round(confidence, 2),
                "data_type": str(df[col].dtype),
                "sample_values": sample_values
            })
        
        return results
    
    def _detect_column_role(self, df: pd.DataFrame, col: str) -> tuple:
        """Detect role for a single column.
        
        Args:
            df: DataFrame
            col: Column name
            
        Returns:
            Tuple of (role, confidence)
        """
        col_lower = col.lower()
        data = df[col]
        
        # TIME detection
        if self._is_time_column(col_lower, data):
            return "TIME", 0.95
        
        # Check if numeric
        if not pd.api.types.is_numeric_dtype(data):
            # Non-numeric likely DIMENSION
            return self._classify_categorical(col_lower, data)
        
        # For numeric columns
        return self._classify_numeric(col_lower, data, df)
    
    def _is_time_column(self, col_name: str, data: pd.Series) -> bool:
        """Check if column is a time column.
        
        Args:
            col_name: Column name
            data: Column data
            
        Returns:
            True if time column
        """
        time_keywords = ['date', 'time', 'datetime', 'timestamp', 'day', 'month', 'year', 'dt']
        
        # Check name
        if any(keyword in col_name for keyword in time_keywords):
            return True
        
        # Try parsing as date
        try:
            pd.to_datetime(data.dropna().head(10))
            return True
        except:
            pass
        
        return False
    
    def _classify_categorical(self, col_name: str, data: pd.Series) -> tuple:
        """Classify categorical column.
        
        Args:
            col_name: Column name
            data: Column data
            
        Returns:
            Tuple of (role, confidence)
        """
        unique_count = data.nunique()
        total_count = len(data)
        cardinality_ratio = unique_count / total_count
        
        # Low cardinality = DIMENSION
        if cardinality_ratio < 0.5:
            return "DIMENSION", 0.85
        
        # High cardinality = likely IGNORE
        return "IGNORE", 0.60
    
    def _classify_numeric(self, col_name: str, data: pd.Series, df: pd.DataFrame) -> tuple:
        """Classify numeric column.
        
        Args:
            col_name: Column name
            data: Column data
            df: Full DataFrame
            
        Returns:
            Tuple of (role, confidence)
        """
        # ACTION keywords (controllable inputs)
        action_keywords = ['spend', 'cost', 'budget', 'investment', 'expense', 
                          'price', 'bid', 'rate', 'allocation']
        
        # OUTCOME keywords (KPIs to optimize)
        outcome_keywords = ['revenue', 'sales', 'profit', 'income', 'earnings',
                           'return', 'roi', 'conversion', 'ctr', 'roas']
        
        # METRIC keywords (supporting metrics)
        metric_keywords = ['click', 'impression', 'view', 'visitor', 'user',
                          'engagement', 'bounce', 'session']
        
        # Check name patterns
        for keyword in action_keywords:
            if keyword in col_name:
                return "ACTION", 0.90
        
        for keyword in outcome_keywords:
            if keyword in col_name:
                return "OUTCOME", 0.90
        
        for keyword in metric_keywords:
            if keyword in col_name:
                return "METRIC", 0.80
        
        # Statistical heuristics
        variance = data.var()
        mean = data.mean()
        cv = abs(variance / mean) if mean != 0 else 0  # Coefficient of variation
        
        # High variance relative to mean suggests ACTION or OUTCOME
        if cv > 0.2:
            # Check correlations with other columns
            correlations = self._calculate_correlations(data, df)
            max_corr = max(correlations.values()) if correlations else 0
            
            if max_corr > 0.7:
                # Highly correlated = likely OUTCOME
                return "OUTCOME", 0.70
            else:
                # Less correlated = likely ACTION
                return "ACTION", 0.65
        
        # Default to METRIC
        return "METRIC", 0.60
    
    def _calculate_correlations(self, data: pd.Series, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate correlations with other numeric columns.
        
        Args:
            data: Column data
            df: Full DataFrame
            
        Returns:
            Dict of correlations
        """
        correlations = {}
        numeric_cols = df.select_dtypes(include=['number']).columns
        
        for col in numeric_cols:
            if col != data.name:
                try:
                    corr = abs(data.corr(df[col]))
                    if not np.isnan(corr):
                        correlations[col] = corr
                except:
                    pass
        
        return correlations
    
    def validate_role_mapping(self, role_mapping: List[Dict[str, str]]) -> Dict[str, Any]:
        """Validate role mapping meets requirements.
        
        Args:
            role_mapping: List of {name, role} mappings
            
        Returns:
            Validation result with errors
        """
        roles = [r["role"] for r in role_mapping]
        role_counts = Counter(roles)
        
        errors = []
        warnings = []
        
        # Check TIME
        if role_counts.get("TIME", 0) == 0:
            errors.append("Exactly one TIME column is required")
        elif role_counts.get("TIME", 0) > 1:
            errors.append("Only one TIME column is allowed")
        
        # Check OUTCOME
        if role_counts.get("OUTCOME", 0) == 0:
            errors.append("Exactly one OUTCOME column is required")
        elif role_counts.get("OUTCOME", 0) > 1:
            errors.append("Only one OUTCOME column is allowed")
        
        # Check ACTION
        if role_counts.get("ACTION", 0) == 0:
            errors.append("At least one ACTION column is required")
        
        # Warnings for missing optional roles
        if role_counts.get("METRIC", 0) == 0:
            warnings.append("No METRIC columns defined (optional)")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "role_counts": dict(role_counts)
        }
    
    def get_columns_by_role(self, role_mapping: List[Dict[str, str]], role: str) -> List[str]:
        """Get column names for a specific role.
        
        Args:
            role_mapping: List of {name, role} mappings
            role: Role to filter by
            
        Returns:
            List of column names
        """
        return [r["name"] for r in role_mapping if r["role"] == role]
