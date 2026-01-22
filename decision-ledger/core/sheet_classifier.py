"""Sheet role classifier using structural signals only.

No hardcoded sheet names or domain keywords.
Classification is based purely on:
- Column structure patterns
- Data type distributions
- Temporal patterns
- Numeric distributions
- Cardinality analysis
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from .ontology import SheetRole, ColumnSemanticType


@dataclass
class SheetProfile:
    """Structural profile of a sheet."""
    name: str
    row_count: int
    col_count: int
    numeric_col_ratio: float
    temporal_col_count: int
    text_col_ratio: float
    null_ratio: float
    unique_ratio_avg: float  # Average uniqueness across columns
    has_aggregations: bool
    has_comparisons: bool
    temporal_coverage: str  # "past", "future", "mixed", "none"
    inferred_role: SheetRole
    confidence: float
    column_profiles: List[Dict[str, Any]]


class SheetClassifier:
    """Classify sheets by role using structural analysis."""
    
    def __init__(self):
        self.profiles: Dict[str, SheetProfile] = {}
    
    def classify_all_sheets(
        self, 
        datasets: Dict[str, pd.DataFrame]
    ) -> Dict[str, SheetProfile]:
        """Classify all sheets in a workbook.
        
        Args:
            datasets: Dict mapping sheet names to DataFrames
            
        Returns:
            Dict mapping sheet names to SheetProfiles
        """
        profiles = {}
        
        for sheet_name, df in datasets.items():
            profile = self._analyze_sheet(sheet_name, df)
            profiles[sheet_name] = profile
        
        # Cross-sheet analysis to refine classifications
        profiles = self._refine_classifications(profiles, datasets)
        
        self.profiles = profiles
        return profiles
    
    def _analyze_sheet(self, name: str, df: pd.DataFrame) -> SheetProfile:
        """Analyze a single sheet's structure."""
        # Filter out unnamed columns before analysis
        cols_to_keep = [c for c in df.columns if not str(c).startswith('Unnamed:')]
        if cols_to_keep:
            df = df[cols_to_keep]
        
        if df.empty or len(df.columns) == 0:
            return SheetProfile(
                name=name,
                row_count=0,
                col_count=0,
                numeric_col_ratio=0.0,
                temporal_col_count=0,
                text_col_ratio=0.0,
                null_ratio=0.0,
                unique_ratio_avg=0.0,
                has_aggregations=False,
                has_comparisons=False,
                temporal_coverage="none",
                inferred_role=SheetRole.UNKNOWN,
                confidence=0.0,
                column_profiles=[]
            )
        
        # Column-level analysis
        column_profiles = []
        numeric_cols = 0
        temporal_cols = 0
        text_cols = 0
        unique_ratios = []
        
        for col in df.columns:
            col_profile = self._analyze_column(df[col], str(col))
            column_profiles.append(col_profile)
            
            if col_profile['semantic_type'] in [
                ColumnSemanticType.QUANTITY,
                ColumnSemanticType.CURRENCY,
                ColumnSemanticType.PERCENTAGE,
                ColumnSemanticType.METRIC
            ]:
                numeric_cols += 1
            elif col_profile['semantic_type'] == ColumnSemanticType.TEMPORAL:
                temporal_cols += 1
            elif col_profile['semantic_type'] in [
                ColumnSemanticType.ENTITY_NAME,
                ColumnSemanticType.REMARK,
                ColumnSemanticType.STATUS
            ]:
                text_cols += 1
            
            unique_ratios.append(col_profile['unique_ratio'])
        
        # Sheet-level metrics
        row_count = len(df)
        col_count = len(df.columns)
        numeric_col_ratio = numeric_cols / col_count if col_count > 0 else 0
        text_col_ratio = text_cols / col_count if col_count > 0 else 0
        null_ratio = df.isnull().sum().sum() / (row_count * col_count) if row_count * col_count > 0 else 0
        unique_ratio_avg = np.mean(unique_ratios) if unique_ratios else 0
        
        # Pattern detection
        has_aggregations = self._detect_aggregations(df, column_profiles)
        has_comparisons = self._detect_comparisons(df, column_profiles)
        temporal_coverage = self._detect_temporal_coverage(df, column_profiles)
        
        # Infer role
        role, confidence = self._infer_role(
            row_count=row_count,
            col_count=col_count,
            numeric_col_ratio=numeric_col_ratio,
            text_col_ratio=text_col_ratio,
            temporal_cols=temporal_cols,
            unique_ratio_avg=unique_ratio_avg,
            has_aggregations=has_aggregations,
            has_comparisons=has_comparisons,
            temporal_coverage=temporal_coverage,
            column_profiles=column_profiles
        )
        
        return SheetProfile(
            name=name,
            row_count=row_count,
            col_count=col_count,
            numeric_col_ratio=numeric_col_ratio,
            temporal_col_count=temporal_cols,
            text_col_ratio=text_col_ratio,
            null_ratio=null_ratio,
            unique_ratio_avg=unique_ratio_avg,
            has_aggregations=has_aggregations,
            has_comparisons=has_comparisons,
            temporal_coverage=temporal_coverage,
            inferred_role=role,
            confidence=confidence,
            column_profiles=column_profiles
        )
    
    def _analyze_column(self, series: pd.Series, col_name: str) -> Dict[str, Any]:
        """Analyze a single column's structure."""
        non_null = series.dropna()
        total_count = len(series)
        non_null_count = len(non_null)
        
        profile = {
            'name': col_name,
            'dtype': str(series.dtype),
            'null_ratio': 1 - (non_null_count / total_count) if total_count > 0 else 1,
            'unique_count': series.nunique(),
            'unique_ratio': series.nunique() / non_null_count if non_null_count > 0 else 0,
            'semantic_type': ColumnSemanticType.UNKNOWN,
            'is_potential_key': False,
            'statistical_profile': {}
        }
        
        if non_null_count == 0:
            return profile
        
        # Determine semantic type based on structure
        profile['semantic_type'] = self._infer_semantic_type(series, col_name)
        
        # Check if potential key (high uniqueness)
        profile['is_potential_key'] = profile['unique_ratio'] > 0.9
        
        # Statistical profile for numeric columns
        if pd.api.types.is_numeric_dtype(series):
            profile['statistical_profile'] = {
                'mean': float(non_null.mean()) if not non_null.empty else None,
                'std': float(non_null.std()) if not non_null.empty else None,
                'min': float(non_null.min()) if not non_null.empty else None,
                'max': float(non_null.max()) if not non_null.empty else None,
                'has_negatives': bool((non_null < 0).any()),
                'all_integers': bool((non_null == non_null.astype(int)).all()) if not non_null.empty else False
            }
        
        return profile
    
    def _infer_semantic_type(self, series: pd.Series, col_name: str) -> ColumnSemanticType:
        """Infer semantic type from column structure (not keywords)."""
        non_null = series.dropna()
        
        if non_null.empty:
            return ColumnSemanticType.UNKNOWN
        
        # Check for temporal
        if self._is_temporal(series):
            return ColumnSemanticType.TEMPORAL
        
        # Check numeric patterns
        if pd.api.types.is_numeric_dtype(series):
            return self._classify_numeric(series)
        
        # Check string patterns
        if series.dtype == 'object':
            return self._classify_text(series)
        
        return ColumnSemanticType.UNKNOWN
    
    def _is_temporal(self, series: pd.Series) -> bool:
        """Check if column contains temporal data."""
        # Already datetime
        if pd.api.types.is_datetime64_any_dtype(series):
            return True
        
        # Try parsing as datetime
        if series.dtype == 'object':
            sample = series.dropna().head(20)
            if len(sample) == 0:
                return False
            
            try:
                parsed = pd.to_datetime(sample, errors='coerce')
                valid_ratio = parsed.notna().sum() / len(sample)
                return valid_ratio > 0.8
            except:
                return False
        
        return False
    
    def _classify_numeric(self, series: pd.Series) -> ColumnSemanticType:
        """Classify numeric column by structural patterns."""
        non_null = series.dropna()
        
        if non_null.empty:
            return ColumnSemanticType.METRIC
        
        # Check for percentage pattern (values 0-1 or 0-100)
        min_val, max_val = non_null.min(), non_null.max()
        
        if 0 <= min_val and max_val <= 1:
            return ColumnSemanticType.PERCENTAGE
        if 0 <= min_val and max_val <= 100:
            # Could be percentage or regular metric
            if non_null.mean() < 50 and non_null.std() < 30:
                return ColumnSemanticType.PERCENTAGE
        
        # Check for currency pattern (larger values, 2 decimal places common)
        if min_val >= 0:
            decimal_places = non_null.apply(lambda x: len(str(x).split('.')[-1]) if '.' in str(x) else 0)
            if (decimal_places == 2).mean() > 0.5 and max_val > 100:
                return ColumnSemanticType.CURRENCY
        
        # Check for ID pattern (sequential integers, high uniqueness)
        unique_ratio = series.nunique() / len(non_null)
        all_integers = (non_null == non_null.astype(int)).all()
        
        if unique_ratio > 0.9 and all_integers:
            return ColumnSemanticType.ENTITY_ID
        
        # Check for quantity (integers, positive)
        if all_integers and min_val >= 0:
            return ColumnSemanticType.QUANTITY
        
        return ColumnSemanticType.METRIC
    
    def _classify_text(self, series: pd.Series) -> ColumnSemanticType:
        """Classify text column by structural patterns."""
        non_null = series.dropna().astype(str)
        
        if non_null.empty:
            return ColumnSemanticType.UNKNOWN
        
        unique_ratio = series.nunique() / len(non_null)
        avg_length = non_null.str.len().mean()
        
        # High uniqueness + moderate length = entity name
        if unique_ratio > 0.8 and 3 < avg_length < 50:
            return ColumnSemanticType.ENTITY_NAME
        
        # Low uniqueness = dimension or status
        if unique_ratio < 0.1:
            if series.nunique() < 10:
                return ColumnSemanticType.STATUS
            return ColumnSemanticType.DIMENSION
        
        # Long text = remark
        if avg_length > 50:
            return ColumnSemanticType.REMARK
        
        # Medium uniqueness, short text = dimension
        if unique_ratio < 0.5:
            return ColumnSemanticType.DIMENSION
        
        return ColumnSemanticType.ENTITY_NAME
    
    def _detect_aggregations(
        self, 
        df: pd.DataFrame, 
        column_profiles: List[Dict]
    ) -> bool:
        """Detect if sheet contains aggregated data."""
        if df.empty or len(df) < 3:
            return False
        
        # Low row count with high numeric ratio suggests summary
        numeric_cols = [p for p in column_profiles 
                       if p['semantic_type'] in [
                           ColumnSemanticType.QUANTITY,
                           ColumnSemanticType.CURRENCY,
                           ColumnSemanticType.METRIC
                       ]]
        
        if len(df) < 20 and len(numeric_cols) > len(column_profiles) * 0.5:
            return True
        
        # Check for aggregation patterns in numeric columns
        for col in df.select_dtypes(include=[np.number]).columns:
            values = df[col].dropna()
            if len(values) < 3:
                continue
            
            # Check if last row is sum of others (common aggregation pattern)
            if len(values) >= 3:
                potential_sum = values.iloc[:-1].sum()
                last_val = values.iloc[-1]
                if abs(potential_sum - last_val) < 0.01 * abs(last_val) if last_val != 0 else potential_sum == 0:
                    return True
        
        return False
    
    def _detect_comparisons(
        self, 
        df: pd.DataFrame, 
        column_profiles: List[Dict]
    ) -> bool:
        """Detect if sheet contains comparison data (plan vs actual, period vs period)."""
        # Look for paired numeric columns
        numeric_profiles = [p for p in column_profiles 
                          if p['semantic_type'] in [
                              ColumnSemanticType.QUANTITY,
                              ColumnSemanticType.CURRENCY,
                              ColumnSemanticType.METRIC,
                              ColumnSemanticType.PERCENTAGE
                          ]]
        
        if len(numeric_profiles) < 2:
            return False
        
        # Check for columns with similar statistical profiles (suggesting comparison)
        for i, p1 in enumerate(numeric_profiles):
            for p2 in numeric_profiles[i+1:]:
                stats1 = p1.get('statistical_profile', {})
                stats2 = p2.get('statistical_profile', {})
                
                if not stats1 or not stats2:
                    continue
                
                # Similar range suggests comparison columns
                if stats1.get('min') and stats2.get('min'):
                    range1 = stats1.get('max', 0) - stats1.get('min', 0)
                    range2 = stats2.get('max', 0) - stats2.get('min', 0)
                    
                    if range1 > 0 and range2 > 0:
                        ratio = min(range1, range2) / max(range1, range2)
                        if ratio > 0.5:  # Similar ranges
                            return True
        
        # Check for difference/variance columns
        for p in column_profiles:
            stats = p.get('statistical_profile', {})
            if stats.get('has_negatives', False):
                # Negative values often indicate differences
                return True
        
        return False
    
    def _detect_temporal_coverage(
        self, 
        df: pd.DataFrame, 
        column_profiles: List[Dict]
    ) -> str:
        """Detect temporal coverage of the data."""
        temporal_cols = [p['name'] for p in column_profiles 
                        if p['semantic_type'] == ColumnSemanticType.TEMPORAL]
        
        if not temporal_cols:
            return "none"
        
        now = pd.Timestamp.now()
        
        for col in temporal_cols:
            try:
                dates = pd.to_datetime(df[col], errors='coerce').dropna()
                if dates.empty:
                    continue
                
                min_date = dates.min()
                max_date = dates.max()
                
                if max_date > now + pd.Timedelta(days=30):
                    if min_date < now:
                        return "mixed"
                    return "future"
                elif min_date < now - pd.Timedelta(days=30):
                    return "past"
            except:
                continue
        
        return "none"
    
    def _infer_role(
        self,
        row_count: int,
        col_count: int,
        numeric_col_ratio: float,
        text_col_ratio: float,
        temporal_cols: int,
        unique_ratio_avg: float,
        has_aggregations: bool,
        has_comparisons: bool,
        temporal_coverage: str,
        column_profiles: List[Dict]
    ) -> Tuple[SheetRole, float]:
        """Infer sheet role from structural signals."""
        scores = {
            SheetRole.MASTER: 0.0,
            SheetRole.TRANSACTIONAL: 0.0,
            SheetRole.PLAN: 0.0,
            SheetRole.ACTUAL: 0.0,
            SheetRole.SUMMARY: 0.0,
            SheetRole.COMPARISON: 0.0
        }
        
        # MASTER: High text ratio, high uniqueness, low temporal
        if text_col_ratio > 0.4 and unique_ratio_avg > 0.6 and temporal_cols == 0:
            scores[SheetRole.MASTER] += 0.4
        if any(p['is_potential_key'] for p in column_profiles):
            scores[SheetRole.MASTER] += 0.2
        
        # TRANSACTIONAL: Has temporal, moderate-high row count, mixed columns
        if temporal_cols > 0 and row_count > 20:
            scores[SheetRole.TRANSACTIONAL] += 0.3
        if temporal_coverage == "past":
            scores[SheetRole.TRANSACTIONAL] += 0.2
        
        # PLAN: Future temporal, numeric heavy
        if temporal_coverage == "future":
            scores[SheetRole.PLAN] += 0.5
        if temporal_coverage == "mixed" and numeric_col_ratio > 0.5:
            scores[SheetRole.PLAN] += 0.3
        
        # ACTUAL: Past temporal, numeric heavy
        if temporal_coverage == "past" and numeric_col_ratio > 0.5:
            scores[SheetRole.ACTUAL] += 0.4
        
        # SUMMARY: Low row count, high numeric, aggregations
        if has_aggregations:
            scores[SheetRole.SUMMARY] += 0.4
        if row_count < 20 and numeric_col_ratio > 0.6:
            scores[SheetRole.SUMMARY] += 0.2
        
        # COMPARISON: Has comparisons, difference columns
        if has_comparisons:
            scores[SheetRole.COMPARISON] += 0.5
        
        # Get best role
        best_role = max(scores, key=scores.get)
        confidence = scores[best_role]
        
        if confidence < 0.2:
            return SheetRole.UNKNOWN, confidence
        
        return best_role, min(confidence, 1.0)
    
    def _refine_classifications(
        self, 
        profiles: Dict[str, SheetProfile],
        datasets: Dict[str, pd.DataFrame]
    ) -> Dict[str, SheetProfile]:
        """Refine classifications using cross-sheet analysis."""
        # If we have both PLAN and no ACTUAL, look for actual in transactional
        has_plan = any(p.inferred_role == SheetRole.PLAN for p in profiles.values())
        has_actual = any(p.inferred_role == SheetRole.ACTUAL for p in profiles.values())
        
        if has_plan and not has_actual:
            # Upgrade highest-confidence TRANSACTIONAL to ACTUAL
            transactional = [
                (name, p) for name, p in profiles.items() 
                if p.inferred_role == SheetRole.TRANSACTIONAL
            ]
            if transactional:
                best = max(transactional, key=lambda x: x[1].confidence)
                profiles[best[0]].inferred_role = SheetRole.ACTUAL
        
        return profiles
