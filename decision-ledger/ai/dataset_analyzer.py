"""Dataset analyzer with structured multi-step pipeline."""

from emergentintegrations.llm.chat import LlmChat, UserMessage, SystemMessage
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import json


class DatasetAnalyzer:
    """Structured dataset analysis pipeline with semantic inference."""
    
    def __init__(self, api_key: str):
        """Initialize analyzer with Claude Sonnet 4.5.
        
        Args:
            api_key: Emergent LLM key
        """
        self.api_key = api_key
        self.analysis_cache = {}
        
    async def analyze_dataset(self, df: pd.DataFrame, role_mapping: List[Dict[str, str]], 
                             dataset_id: str) -> Dict[str, Any]:
        """Run complete structured analysis pipeline.
        
        Args:
            df: DataFrame to analyze
            role_mapping: Column role assignments
            dataset_id: Dataset identifier
            
        Returns:
            Complete structured analysis
        """
        # Step 1: File structure analysis (no inference)
        structure = self._analyze_structure(df)
        
        # Step 2: Statistical profiling
        stats = self._generate_statistics(df, role_mapping)
        
        # Step 3: Semantic inference with Claude
        semantics = await self._semantic_inference(df, role_mapping, structure, stats)
        
        # Step 4: Time series detection
        time_series = self._detect_time_series_properties(df, role_mapping)
        
        # Step 5: Metric validation
        metrics = self._validate_metrics(df, role_mapping, stats)
        
        # Complete analysis
        analysis = {
            "dataset_id": dataset_id,
            "structure": structure,
            "statistics": stats,
            "semantic_analysis": semantics,
            "time_series_properties": time_series,
            "metric_validation": metrics,
            "confidence_score": self._calculate_confidence(structure, stats, semantics)
        }
        
        # Cache for chat access
        self.analysis_cache[dataset_id] = analysis
        
        return analysis
    
    def _analyze_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Step 1: Pure structural analysis without inference.
        
        Args:
            df: DataFrame
            
        Returns:
            Structure summary
        """
        return {
            "file_type": "CSV",
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "column_names": list(df.columns),
            "data_types": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024 / 1024
        }
    
    def _generate_statistics(self, df: pd.DataFrame, role_mapping: List[Dict[str, str]]) -> Dict[str, Any]:
        """Step 2: Statistical profiling by role.
        
        Args:
            df: DataFrame
            role_mapping: Role assignments
            
        Returns:
            Statistical summary
        """
        stats = {}
        
        for col_map in role_mapping:
            col_name = col_map["name"]
            role = col_map["role"]
            
            if col_name not in df.columns:
                continue
            
            col_data = df[col_name]
            
            col_stats = {
                "role": role,
                "count": int(col_data.count()),
                "missing": int(col_data.isna().sum()),
                "unique": int(col_data.nunique())
            }
            
            # Numeric stats
            if pd.api.types.is_numeric_dtype(col_data):
                col_stats.update({
                    "mean": float(col_data.mean()) if not col_data.isna().all() else None,
                    "median": float(col_data.median()) if not col_data.isna().all() else None,
                    "std": float(col_data.std()) if not col_data.isna().all() else None,
                    "min": float(col_data.min()) if not col_data.isna().all() else None,
                    "max": float(col_data.max()) if not col_data.isna().all() else None,
                    "q25": float(col_data.quantile(0.25)) if not col_data.isna().all() else None,
                    "q75": float(col_data.quantile(0.75)) if not col_data.isna().all() else None
                })
            
            stats[col_name] = col_stats
        
        return stats
    
    async def _semantic_inference(self, df: pd.DataFrame, role_mapping: List[Dict[str, str]],
                                  structure: Dict, stats: Dict) -> Dict[str, Any]:
        """Step 3: Semantic inference using Claude Sonnet 4.5.
        
        Args:
            df: DataFrame
            role_mapping: Role assignments
            structure: Structural analysis
            stats: Statistical summary
            
        Returns:
            Semantic interpretation
        """
        # Prepare context for Claude
        sample_data = df.head(5).to_dict('records')
        
        prompt = f"""You are analyzing a business dataset for ChanksHQ.

DATASET STRUCTURE:
{json.dumps(structure, indent=2)}

COLUMN ROLES:
{json.dumps(role_mapping, indent=2)}

STATISTICS:
{json.dumps(stats, indent=2)}

SAMPLE DATA (first 5 rows):
{json.dumps(sample_data, indent=2)}

Provide semantic interpretation:
1. What business domain is this data from? (marketing, finance, operations, etc.)
2. What is the primary business metric being tracked?
3. What time granularity is represented? (daily, weekly, monthly)
4. What are the key relationships between ACTION and OUTCOME columns?
5. Are there any data quality concerns?

Return ONLY valid JSON:
{{
  "business_domain": "...",
  "primary_metric": "...",
  "time_granularity": "...",
  "key_relationships": ["..."],
  "data_quality_score": 0.0-1.0,
  "concerns": ["..."]
}}"""

        try:
            chat = LlmChat(
                api_key=self.api_key,
                model="claude-sonnet-4.5",
                session_id=f"semantic_analysis"
            )
            
            response = await chat.send_message_async(UserMessage(content=prompt))
            
            # Parse JSON response
            semantic_result = json.loads(response.content)
            
            return semantic_result
            
        except Exception as e:
            # Fallback if Claude fails
            return {
                "business_domain": "unknown",
                "primary_metric": "unknown",
                "time_granularity": "unknown",
                "key_relationships": [],
                "data_quality_score": 0.5,
                "concerns": [f"Semantic analysis failed: {str(e)}"]
            }
    
    def _detect_time_series_properties(self, df: pd.DataFrame, 
                                      role_mapping: List[Dict[str, str]]) -> Dict[str, Any]:
        """Step 4: Detect time series properties.
        
        Args:
            df: DataFrame
            role_mapping: Role assignments
            
        Returns:
            Time series properties
        """
        # Find TIME column
        time_col = None
        for col_map in role_mapping:
            if col_map["role"] == "TIME":
                time_col = col_map["name"]
                break
        
        if not time_col or time_col not in df.columns:
            return {"has_time_series": False}
        
        time_data = pd.to_datetime(df[time_col], errors='coerce')
        
        # Detect frequency
        if len(time_data.dropna()) > 1:
            time_diff = time_data.diff().dropna()
            median_diff = time_diff.median()
            
            if median_diff <= pd.Timedelta(days=1):
                frequency = "daily"
            elif median_diff <= pd.Timedelta(days=7):
                frequency = "weekly"
            elif median_diff <= pd.Timedelta(days=31):
                frequency = "monthly"
            else:
                frequency = "irregular"
        else:
            frequency = "unknown"
        
        return {
            "has_time_series": True,
            "time_column": time_col,
            "frequency": frequency,
            "date_range": {
                "start": str(time_data.min()),
                "end": str(time_data.max())
            },
            "total_periods": int(time_data.count()),
            "missing_periods": int(time_data.isna().sum())
        }
    
    def _validate_metrics(self, df: pd.DataFrame, role_mapping: List[Dict[str, str]],
                         stats: Dict) -> Dict[str, Any]:
        """Step 5: Validate metrics for modeling readiness.
        
        Args:
            df: DataFrame
            role_mapping: Role assignments
            stats: Statistics
            
        Returns:
            Validation results
        """
        validations = {}
        
        # Check ACTION columns
        action_cols = [r["name"] for r in role_mapping if r["role"] == "ACTION"]
        outcome_cols = [r["name"] for r in role_mapping if r["role"] == "OUTCOME"]
        
        for col in action_cols + outcome_cols:
            if col not in stats:
                continue
            
            col_stats = stats[col]
            
            validations[col] = {
                "completeness": 1.0 - (col_stats["missing"] / col_stats["count"]) if col_stats["count"] > 0 else 0,
                "variance": col_stats.get("std", 0) > 0,
                "sufficient_samples": col_stats["count"] >= 10,
                "ready_for_modeling": True
            }
            
            # Check if ready
            if validations[col]["completeness"] < 0.8:
                validations[col]["ready_for_modeling"] = False
            if not validations[col]["variance"]:
                validations[col]["ready_for_modeling"] = False
            if not validations[col]["sufficient_samples"]:
                validations[col]["ready_for_modeling"] = False
        
        return validations
    
    def _calculate_confidence(self, structure: Dict, stats: Dict, 
                             semantics: Dict) -> float:
        """Calculate overall confidence score.
        
        Args:
            structure: Structure analysis
            stats: Statistics
            semantics: Semantic analysis
            
        Returns:
            Confidence score 0-1
        """
        factors = []
        
        # Data completeness
        if stats:
            total_missing = sum(s.get("missing", 0) for s in stats.values())
            total_count = sum(s.get("count", 0) for s in stats.values())
            if total_count > 0:
                completeness = 1.0 - (total_missing / total_count)
                factors.append(completeness)
        
        # Sample size
        if structure["total_rows"] >= 100:
            factors.append(1.0)
        elif structure["total_rows"] >= 10:
            factors.append(0.7)
        else:
            factors.append(0.3)
        
        # Data quality from semantic analysis
        factors.append(semantics.get("data_quality_score", 0.5))
        
        return sum(factors) / len(factors) if factors else 0.5
    
    def get_cached_analysis(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached analysis for chat access.
        
        Args:
            dataset_id: Dataset identifier
            
        Returns:
            Cached analysis or None
        """
        return self.analysis_cache.get(dataset_id)
