"""Gap analyzer - detects gaps between plan and actual data.

Uses structural patterns to identify:
- Plan vs Actual column pairs
- Period-over-period comparisons
- Target vs Result mismatches
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass

from .ontology import Gap, Plan, Actual, Entity
from .sheet_classifier import SheetProfile, SheetRole
from .entity_detector import EntityDetector


@dataclass
class ColumnPair:
    """A detected plan-actual column pair."""
    plan_column: str
    actual_column: str
    sheet_name: str
    correlation: float
    confidence: float


class GapAnalyzer:
    """Analyze gaps between planned and actual values."""
    
    def __init__(self):
        self.gaps: List[Gap] = []
        self.plans: List[Plan] = []
        self.actuals: List[Actual] = []
        self.column_pairs: List[ColumnPair] = []
    
    def analyze_gaps(
        self,
        datasets: Dict[str, pd.DataFrame],
        entities: Dict[str, Entity],
        entity_detector: EntityDetector,
        sheet_profiles: Dict[str, SheetProfile]
    ) -> Tuple[List[Gap], List[Plan], List[Actual]]:
        """Analyze all datasets for plan-actual gaps.
        
        Args:
            datasets: Sheet data
            entities: Detected entities
            entity_detector: Entity detector
            sheet_profiles: Sheet classifications
            
        Returns:
            Tuple of (gaps, plans, actuals)
        """
        # Strategy 1: Find explicit plan/actual sheets
        self._analyze_separate_sheets(datasets, entities, entity_detector, sheet_profiles)
        
        # Strategy 2: Find plan/actual column pairs within sheets
        self._analyze_column_pairs(datasets, entities, entity_detector, sheet_profiles)
        
        # Strategy 3: Find comparison sheets
        self._analyze_comparison_sheets(datasets, entities, entity_detector, sheet_profiles)
        
        return self.gaps, self.plans, self.actuals
    
    def _analyze_separate_sheets(
        self,
        datasets: Dict[str, pd.DataFrame],
        entities: Dict[str, Entity],
        entity_detector: EntityDetector,
        sheet_profiles: Dict[str, SheetProfile]
    ):
        """Find gaps between separate plan and actual sheets."""
        plan_sheets = [
            name for name, profile in sheet_profiles.items()
            if profile.inferred_role == SheetRole.PLAN
        ]
        actual_sheets = [
            name for name, profile in sheet_profiles.items()
            if profile.inferred_role in [SheetRole.ACTUAL, SheetRole.TRANSACTIONAL]
        ]
        
        for plan_sheet in plan_sheets:
            plan_df = datasets.get(plan_sheet)
            if plan_df is None:
                continue
            
            for actual_sheet in actual_sheets:
                actual_df = datasets.get(actual_sheet)
                if actual_df is None:
                    continue
                
                # Find common entity columns
                common_entities = self._find_common_entities(
                    plan_df, actual_df, plan_sheet, actual_sheet, entity_detector
                )
                
                if not common_entities:
                    continue
                
                # Find comparable metric columns
                metric_pairs = self._match_metric_columns(plan_df, actual_df)
                
                for entity_col in common_entities:
                    for plan_metric, actual_metric in metric_pairs:
                        self._extract_gaps_from_sheets(
                            plan_df, actual_df,
                            entity_col, plan_metric, actual_metric,
                            plan_sheet, actual_sheet,
                            entities, entity_detector
                        )
    
    def _analyze_column_pairs(
        self,
        datasets: Dict[str, pd.DataFrame],
        entities: Dict[str, Entity],
        entity_detector: EntityDetector,
        sheet_profiles: Dict[str, SheetProfile]
    ):
        """Find plan-actual column pairs within single sheets."""
        for sheet_name, df in datasets.items():
            profile = sheet_profiles.get(sheet_name)
            if not profile:
                continue
            
            # Get numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            
            if len(numeric_cols) < 2:
                continue
            
            # Find pairs that look like plan vs actual
            pairs = self._detect_comparison_pairs(df, numeric_cols)
            
            for pair in pairs:
                self.column_pairs.append(ColumnPair(
                    plan_column=pair[0],
                    actual_column=pair[1],
                    sheet_name=sheet_name,
                    correlation=pair[2],
                    confidence=pair[3]
                ))
                
                # Extract gaps from this pair
                self._extract_gaps_from_columns(
                    df, pair[0], pair[1], sheet_name,
                    entities, entity_detector
                )
    
    def _analyze_comparison_sheets(
        self,
        datasets: Dict[str, pd.DataFrame],
        entities: Dict[str, Entity],
        entity_detector: EntityDetector,
        sheet_profiles: Dict[str, SheetProfile]
    ):
        """Analyze sheets explicitly marked as comparisons."""
        comparison_sheets = [
            name for name, profile in sheet_profiles.items()
            if profile.inferred_role == SheetRole.COMPARISON or profile.has_comparisons
        ]
        
        for sheet_name in comparison_sheets:
            df = datasets.get(sheet_name)
            if df is None:
                continue
            
            # Look for difference/variance columns
            self._analyze_difference_columns(
                df, sheet_name, entities, entity_detector
            )
    
    def _find_common_entities(
        self,
        df1: pd.DataFrame,
        df2: pd.DataFrame,
        sheet1: str,
        sheet2: str,
        entity_detector: EntityDetector
    ) -> List[str]:
        """Find entity columns common to both dataframes."""
        common = []
        
        for col1 in df1.columns:
            entity1 = entity_detector.get_entity_for_column(sheet1, str(col1))
            if not entity1:
                continue
            
            for col2 in df2.columns:
                entity2 = entity_detector.get_entity_for_column(sheet2, str(col2))
                if entity2 and entity1.id == entity2.id:
                    common.append(str(col1))
                    break
        
        return common
    
    def _match_metric_columns(
        self,
        plan_df: pd.DataFrame,
        actual_df: pd.DataFrame
    ) -> List[Tuple[str, str]]:
        """Match metric columns between plan and actual sheets."""
        plan_numeric = plan_df.select_dtypes(include=[np.number]).columns
        actual_numeric = actual_df.select_dtypes(include=[np.number]).columns
        
        pairs = []
        
        for plan_col in plan_numeric:
            best_match = None
            best_score = 0
            
            for actual_col in actual_numeric:
                # Score based on statistical similarity
                score = self._column_similarity_score(
                    plan_df[plan_col], actual_df[actual_col]
                )
                
                if score > best_score:
                    best_score = score
                    best_match = actual_col
            
            if best_match and best_score > 0.3:
                pairs.append((str(plan_col), str(best_match)))
        
        return pairs
    
    def _column_similarity_score(
        self,
        series1: pd.Series,
        series2: pd.Series
    ) -> float:
        """Calculate similarity score between two numeric columns."""
        s1 = series1.dropna()
        s2 = series2.dropna()
        
        if s1.empty or s2.empty:
            return 0.0
        
        # Compare ranges
        range1 = s1.max() - s1.min()
        range2 = s2.max() - s2.min()
        
        if range1 == 0 or range2 == 0:
            return 0.0
        
        range_ratio = min(range1, range2) / max(range1, range2)
        
        # Compare means
        mean1, mean2 = s1.mean(), s2.mean()
        if mean1 == 0 and mean2 == 0:
            mean_ratio = 1.0
        elif mean1 == 0 or mean2 == 0:
            mean_ratio = 0.0
        else:
            mean_ratio = min(abs(mean1), abs(mean2)) / max(abs(mean1), abs(mean2))
        
        return 0.5 * range_ratio + 0.5 * mean_ratio
    
    def _detect_comparison_pairs(
        self,
        df: pd.DataFrame,
        numeric_cols: List[str]
    ) -> List[Tuple[str, str, float, float]]:
        """Detect column pairs that look like comparisons."""
        pairs = []
        
        for i, col1 in enumerate(numeric_cols):
            for col2 in numeric_cols[i+1:]:
                # Calculate correlation
                try:
                    corr = df[col1].corr(df[col2])
                    if pd.isna(corr):
                        continue
                except:
                    continue
                
                # High correlation suggests comparison pair
                if corr > 0.7:
                    # Check if one could be plan, other actual
                    # Plan often has less variance (smoother targets)
                    var1 = df[col1].var()
                    var2 = df[col2].var()
                    
                    if var1 > 0 and var2 > 0:
                        var_ratio = min(var1, var2) / max(var1, var2)
                        
                        # Different variances suggest plan vs actual
                        if var_ratio < 0.8:
                            # Lower variance is likely plan
                            if var1 < var2:
                                pairs.append((col1, col2, corr, 0.7))
                            else:
                                pairs.append((col2, col1, corr, 0.7))
        
        return pairs
    
    def _extract_gaps_from_sheets(
        self,
        plan_df: pd.DataFrame,
        actual_df: pd.DataFrame,
        entity_col: str,
        plan_metric: str,
        actual_metric: str,
        plan_sheet: str,
        actual_sheet: str,
        entities: Dict[str, Entity],
        entity_detector: EntityDetector
    ):
        """Extract gaps from separate plan and actual sheets."""
        # Merge on entity column
        merged = pd.merge(
            plan_df[[entity_col, plan_metric]].rename(columns={plan_metric: 'plan'}),
            actual_df[[entity_col, actual_metric]].rename(columns={actual_metric: 'actual'}),
            on=entity_col,
            how='outer'
        )
        
        for _, row in merged.iterrows():
            plan_val = row.get('plan')
            actual_val = row.get('actual')
            entity_val = row.get(entity_col)
            
            if pd.isna(plan_val) or pd.isna(actual_val):
                continue
            
            # Create gap
            gap = self._create_gap(
                entity_val=str(entity_val),
                metric_name=plan_metric,
                plan_value=float(plan_val),
                actual_value=float(actual_val),
                entity_detector=entity_detector,
                entities=entities,
                plan_sheet=plan_sheet
            )
            
            if gap:
                self.gaps.append(gap)
    
    def _extract_gaps_from_columns(
        self,
        df: pd.DataFrame,
        plan_col: str,
        actual_col: str,
        sheet_name: str,
        entities: Dict[str, Entity],
        entity_detector: EntityDetector
    ):
        """Extract gaps from column pairs within a sheet."""
        # Find entity column in this sheet
        entity_col = None
        for col in df.columns:
            entity = entity_detector.get_entity_for_column(sheet_name, str(col))
            if entity and entity.is_primary:
                entity_col = str(col)
                break
        
        for idx, row in df.iterrows():
            plan_val = row.get(plan_col)
            actual_val = row.get(actual_col)
            
            if pd.isna(plan_val) or pd.isna(actual_val):
                continue
            
            entity_val = str(row.get(entity_col)) if entity_col else f"row_{idx}"
            
            gap = self._create_gap(
                entity_val=entity_val,
                metric_name=plan_col,
                plan_value=float(plan_val),
                actual_value=float(actual_val),
                entity_detector=entity_detector,
                entities=entities,
                plan_sheet=sheet_name
            )
            
            if gap:
                self.gaps.append(gap)
    
    def _analyze_difference_columns(
        self,
        df: pd.DataFrame,
        sheet_name: str,
        entities: Dict[str, Entity],
        entity_detector: EntityDetector
    ):
        """Analyze columns that contain pre-computed differences."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            series = df[col].dropna()
            
            # Check if this column contains differences (has negatives, centered around 0)
            if series.empty:
                continue
            
            has_negatives = (series < 0).any()
            near_zero_mean = abs(series.mean()) < series.std() * 0.5 if series.std() > 0 else False
            
            if has_negatives and near_zero_mean:
                # This looks like a difference/variance column
                # Create gaps from non-zero values
                for idx, val in series.items():
                    if abs(val) > 0.01:  # Non-trivial difference
                        # Find entity for this row
                        entity_col = None
                        for c in df.columns:
                            entity = entity_detector.get_entity_for_column(sheet_name, str(c))
                            if entity:
                                entity_col = str(c)
                                break
                        
                        entity_val = str(df.loc[idx, entity_col]) if entity_col else f"row_{idx}"
                        
                        gap = Gap(
                            entity_id=entity_val,
                            metric_name=str(col),
                            plan_value=None,  # Unknown from difference alone
                            actual_value=None,
                            absolute_gap=float(val),
                            percentage_gap=0.0,  # Can't calculate without base
                            direction="under" if val < 0 else "over",
                            severity=self._calculate_severity_from_diff(val, series)
                        )
                        self.gaps.append(gap)
    
    def _create_gap(
        self,
        entity_val: str,
        metric_name: str,
        plan_value: float,
        actual_value: float,
        entity_detector: EntityDetector,
        entities: Dict[str, Entity],
        plan_sheet: str
    ) -> Optional[Gap]:
        """Create a Gap object from plan and actual values."""
        absolute_gap = actual_value - plan_value
        
        if plan_value != 0:
            percentage_gap = (absolute_gap / plan_value) * 100
        else:
            percentage_gap = 100.0 if actual_value != 0 else 0.0
        
        # Determine direction
        if abs(percentage_gap) < 5:
            direction = "on_target"
        elif actual_value < plan_value:
            direction = "under"
        else:
            direction = "over"
        
        # Determine severity
        severity = self._calculate_severity(percentage_gap)
        
        # Find entity ID
        entity_id = entity_val
        matches = entity_detector.find_entities_by_value(entity_val)
        if matches:
            entity_id = matches[0].id
        
        # Record plan and actual
        plan = Plan(
            entity_id=entity_id,
            metric_name=metric_name,
            target_value=plan_value,
            source_sheet=plan_sheet,
            confidence=0.8
        )
        self.plans.append(plan)
        
        actual = Actual(
            entity_id=entity_id,
            metric_name=metric_name,
            actual_value=actual_value,
            confidence=0.8
        )
        self.actuals.append(actual)
        
        return Gap(
            entity_id=entity_id,
            metric_name=metric_name,
            plan_value=plan_value,
            actual_value=actual_value,
            absolute_gap=absolute_gap,
            percentage_gap=percentage_gap,
            direction=direction,
            severity=severity
        )
    
    def _calculate_severity(self, percentage_gap: float) -> str:
        """Calculate severity based on percentage gap."""
        abs_gap = abs(percentage_gap)
        
        if abs_gap < 5:
            return "normal"
        elif abs_gap < 15:
            return "warning"
        else:
            return "critical"
    
    def _calculate_severity_from_diff(
        self, 
        diff_value: float, 
        all_diffs: pd.Series
    ) -> str:
        """Calculate severity based on difference value relative to distribution."""
        std = all_diffs.std()
        if std == 0:
            return "normal"
        
        z_score = abs(diff_value) / std
        
        if z_score < 1:
            return "normal"
        elif z_score < 2:
            return "warning"
        else:
            return "critical"
    
    def get_critical_gaps(self) -> List[Gap]:
        """Get all critical severity gaps."""
        return [g for g in self.gaps if g.severity == "critical"]
    
    def get_gaps_by_entity(self, entity_id: str) -> List[Gap]:
        """Get all gaps for a specific entity."""
        return [g for g in self.gaps if g.entity_id == entity_id]
