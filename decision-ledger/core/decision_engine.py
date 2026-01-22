"""Decision Intelligence Engine - Industry-agnostic enterprise workbook analysis.

This is the main orchestrator that:
1. Classifies sheets by structural role
2. Normalizes data into clean dataframes
3. Detects entities across sheets
4. Builds entity relationship graph
5. Detects metrics and dimensions
6. Identifies plan-actual gaps
7. Extracts constraints from text
8. Generates decision candidates
9. Records to decision ledger

No domain-specific logic. Pure structural and statistical analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import json

from .ontology import (
    DecisionContext, Decision, Entity, Gap, Constraint,
    Plan, Actual, Action, SheetRole
)
from .sheet_classifier import SheetClassifier, SheetProfile
from .entity_detector import EntityDetector
from .relationship_graph import RelationshipGraph
from .gap_analyzer import GapAnalyzer
from .constraint_extractor import ConstraintExtractor
from .decision_generator import DecisionGenerator


@dataclass
class AnalysisResult:
    """Complete analysis result from the decision engine."""
    dataset_id: str
    analyzed_at: str
    
    # Sheet analysis
    sheet_count: int
    sheet_roles: Dict[str, str]
    sheet_profiles: Dict[str, Dict[str, Any]]
    
    # Entity analysis
    entity_count: int
    entities: List[Dict[str, Any]]
    entity_graph: Dict[str, List[str]]
    
    # Gap analysis
    gap_count: int
    critical_gaps: int
    gaps: List[Dict[str, Any]]
    plans: List[Dict[str, Any]]
    actuals: List[Dict[str, Any]]
    
    # Constraint analysis
    constraint_count: int
    blocking_constraints: int
    constraints: List[Dict[str, Any]]
    
    # Decision candidates
    decision_count: int
    decisions: List[Dict[str, Any]]
    top_decision_summary: str
    
    # Metadata
    processing_notes: List[str]


class DecisionIntelligenceEngine:
    """Industry-agnostic decision intelligence engine.
    
    Analyzes any enterprise workbook to infer:
    - What entities are being tracked
    - What metrics matter
    - Where are the gaps between plan and actual
    - What constraints exist
    - What decisions need to be made
    """
    
    def __init__(self):
        self.sheet_classifier = SheetClassifier()
        self.entity_detector = EntityDetector()
        self.relationship_graph = RelationshipGraph()
        self.gap_analyzer = GapAnalyzer()
        self.constraint_extractor = ConstraintExtractor()
        self.decision_generator = DecisionGenerator()
        
        self.context: Optional[DecisionContext] = None
        self.processing_notes: List[str] = []
    
    def analyze(
        self,
        datasets: Dict[str, pd.DataFrame],
        dataset_id: str
    ) -> AnalysisResult:
        """Run complete analysis on a workbook.
        
        Args:
            datasets: Dict mapping sheet names to DataFrames
            dataset_id: Unique identifier for this dataset
            
        Returns:
            Complete AnalysisResult with all findings
        """
        self.processing_notes = []
        self._log(f"Starting analysis of {len(datasets)} sheets")
        
        # Initialize context
        self.context = DecisionContext(
            metadata={'dataset_id': dataset_id, 'sheet_count': len(datasets)}
        )
        
        # Step 1: Normalize dataframes FIRST (before classification)
        self._log("Step 1: Normalizing data...")
        normalized_datasets = self._normalize_datasets(datasets, {})
        
        # Step 2: Classify sheets by structural role (on normalized data)
        self._log("Step 2: Classifying sheet roles...")
        sheet_profiles = self._classify_sheets(normalized_datasets)
        
        # Step 3: Detect entities
        self._log("Step 3: Detecting entities...")
        entities = self._detect_entities(normalized_datasets, sheet_profiles)
        
        # Step 4: Build relationship graph
        self._log("Step 4: Building entity relationship graph...")
        entity_graph = self._build_relationship_graph(
            normalized_datasets, entities, sheet_profiles
        )
        
        # Step 5: Detect metrics and dimensions
        self._log("Step 5: Detecting metrics and dimensions...")
        self._detect_metrics_dimensions(normalized_datasets, sheet_profiles)
        
        # Step 6: Analyze gaps
        self._log("Step 6: Analyzing plan-actual gaps...")
        gaps, plans, actuals = self._analyze_gaps(
            normalized_datasets, entities, sheet_profiles
        )
        
        # Step 7: Extract constraints
        self._log("Step 7: Extracting constraints...")
        constraints = self._extract_constraints(
            normalized_datasets, entities, sheet_profiles
        )
        
        # Step 8: Generate decisions
        self._log("Step 8: Generating decision candidates...")
        decisions = self._generate_decisions()
        
        # Step 9: Build result
        self._log("Step 9: Compiling results...")
        result = self._build_result(
            dataset_id, datasets, sheet_profiles,
            entities, entity_graph, gaps, plans, actuals,
            constraints, decisions
        )
        
        self._log(f"Analysis complete. Found {result.decision_count} decision candidates.")
        
        return result
    
    def _log(self, message: str):
        """Add a processing note."""
        self.processing_notes.append(f"[{datetime.utcnow().isoformat()}] {message}")
    
    def _classify_sheets(
        self,
        datasets: Dict[str, pd.DataFrame]
    ) -> Dict[str, SheetProfile]:
        """Classify all sheets by structural role."""
        profiles = self.sheet_classifier.classify_all_sheets(datasets)
        
        # Log classification results
        for name, profile in profiles.items():
            self._log(
                f"  Sheet '{name}': {profile.inferred_role.value} "
                f"(confidence: {profile.confidence:.2f})"
            )
        
        return profiles
    
    def _normalize_datasets(
        self,
        datasets: Dict[str, pd.DataFrame],
        sheet_profiles: Dict[str, SheetProfile]
    ) -> Dict[str, pd.DataFrame]:
        """Normalize all dataframes for consistent processing."""
        normalized = {}
        
        for name, df in datasets.items():
            # Skip empty sheets
            if df.empty:
                continue
            
            # Clean column names
            df = df.copy()
            df.columns = [str(c).strip() for c in df.columns]
            
            # Remove unnamed/index columns
            unnamed_cols = [c for c in df.columns if c.startswith('Unnamed:')]
            if unnamed_cols:
                df = df.drop(columns=unnamed_cols)
            
            # Skip if no columns left
            if df.empty or len(df.columns) == 0:
                continue
            
            # Remove completely empty rows/columns
            df = df.dropna(how='all', axis=0)
            df = df.dropna(how='all', axis=1)
            
            # Skip if empty after cleaning
            if df.empty:
                continue
            
            # Handle duplicate column names
            cols = pd.Series(df.columns)
            for dup in cols[cols.duplicated()].unique():
                dup_mask = cols == dup
                cols[dup_mask] = [f"{dup}_{i}" for i in range(dup_mask.sum())]
            df.columns = cols
            
            normalized[name] = df
        
        return normalized
    
    def _detect_entities(
        self,
        datasets: Dict[str, pd.DataFrame],
        sheet_profiles: Dict[str, SheetProfile]
    ) -> Dict[str, Entity]:
        """Detect entities across all sheets."""
        entities = self.entity_detector.detect_entities(datasets, sheet_profiles)
        
        # Update context
        self.context.entities = entities
        
        self._log(f"  Detected {len(entities)} unique entities")
        
        return entities
    
    def _build_relationship_graph(
        self,
        datasets: Dict[str, pd.DataFrame],
        entities: Dict[str, Entity],
        sheet_profiles: Dict[str, SheetProfile]
    ) -> Dict[str, List[str]]:
        """Build entity relationship graph."""
        graph = self.relationship_graph.build_graph(
            datasets, entities, self.entity_detector, sheet_profiles
        )
        
        # Update context
        self.context.entity_graph = {k: v for k, v in graph.items()}
        
        # Count relationships
        rel_count = len(self.relationship_graph.relationships)
        self._log(f"  Built graph with {rel_count} relationships")
        
        return {k: list(v) for k, v in graph.items()}
    
    def _detect_metrics_dimensions(
        self,
        datasets: Dict[str, pd.DataFrame],
        sheet_profiles: Dict[str, SheetProfile]
    ):
        """Detect global metrics and dimensions."""
        # This is captured in sheet profiles during classification
        # Aggregate metrics across sheets
        all_metrics = set()
        all_dimensions = set()
        
        for profile in sheet_profiles.values():
            for col_profile in profile.column_profiles:
                semantic_type = col_profile.get('semantic_type')
                col_name = col_profile['name']
                
                if semantic_type and semantic_type.value in ['quantity', 'currency', 'metric', 'percentage']:
                    all_metrics.add(col_name)
                elif semantic_type and semantic_type.value == 'dimension':
                    all_dimensions.add(col_name)
        
        self.context.metadata['global_metrics'] = list(all_metrics)
        self.context.metadata['global_dimensions'] = list(all_dimensions)
        
        self._log(f"  Found {len(all_metrics)} metrics, {len(all_dimensions)} dimensions")
    
    def _analyze_gaps(
        self,
        datasets: Dict[str, pd.DataFrame],
        entities: Dict[str, Entity],
        sheet_profiles: Dict[str, SheetProfile]
    ) -> Tuple[List[Gap], List[Plan], List[Actual]]:
        """Analyze plan-actual gaps."""
        gaps, plans, actuals = self.gap_analyzer.analyze_gaps(
            datasets, entities, self.entity_detector, sheet_profiles
        )
        
        # Update context
        self.context.gaps = gaps
        self.context.plans = plans
        self.context.actuals = actuals
        
        critical_count = len(self.gap_analyzer.get_critical_gaps())
        self._log(f"  Found {len(gaps)} gaps ({critical_count} critical)")
        
        return gaps, plans, actuals
    
    def _extract_constraints(
        self,
        datasets: Dict[str, pd.DataFrame],
        entities: Dict[str, Entity],
        sheet_profiles: Dict[str, SheetProfile]
    ) -> List[Constraint]:
        """Extract constraints from text fields."""
        constraints = self.constraint_extractor.extract_constraints(
            datasets, entities, self.entity_detector, sheet_profiles
        )
        
        # Update context
        self.context.constraints = constraints
        
        blocking_count = len(self.constraint_extractor.get_blocking_constraints())
        self._log(f"  Extracted {len(constraints)} constraints ({blocking_count} blocking)")
        
        return constraints
    
    def _generate_decisions(self) -> List[Decision]:
        """Generate decision candidates."""
        decisions = self.decision_generator.generate_decisions(
            self.context, self.relationship_graph
        )
        
        # Update context
        self.context.decisions = decisions
        self.context.actions = self.decision_generator.actions
        
        return decisions
    
    def _build_result(
        self,
        dataset_id: str,
        datasets: Dict[str, pd.DataFrame],
        sheet_profiles: Dict[str, SheetProfile],
        entities: Dict[str, Entity],
        entity_graph: Dict[str, List[str]],
        gaps: List[Gap],
        plans: List[Plan],
        actuals: List[Actual],
        constraints: List[Constraint],
        decisions: List[Decision]
    ) -> AnalysisResult:
        """Build the final analysis result."""
        # Convert entities to serializable format
        entity_list = []
        for entity in entities.values():
            entity_list.append({
                'id': entity.id,
                'canonical_name': entity.canonical_name,
                'source_columns': entity.source_columns,
                'source_sheets': entity.source_sheets,
                'cardinality': entity.cardinality,
                'is_primary': entity.is_primary,
                'related_count': len(entity.related_entities)
            })
        
        # Convert gaps
        gap_list = []
        for gap in gaps:
            gap_list.append({
                'id': gap.id,
                'entity_id': gap.entity_id,
                'metric_name': gap.metric_name,
                'plan_value': self._safe_float(gap.plan_value),
                'actual_value': self._safe_float(gap.actual_value),
                'absolute_gap': self._safe_float(gap.absolute_gap),
                'percentage_gap': self._safe_float(gap.percentage_gap),
                'direction': gap.direction,
                'severity': gap.severity
            })
        
        # Convert plans/actuals
        plan_list = [{
            'entity_id': p.entity_id,
            'metric_name': p.metric_name,
            'target_value': self._safe_float(p.target_value),
            'source_sheet': p.source_sheet
        } for p in plans]
        
        actual_list = [{
            'entity_id': a.entity_id,
            'metric_name': a.metric_name,
            'actual_value': self._safe_float(a.actual_value),
            'source_sheet': a.source_sheet
        } for a in actuals]
        
        # Convert constraints
        constraint_list = [{
            'id': c.id,
            'entity_id': c.entity_id,
            'constraint_type': c.constraint_type,
            'description': c.description,
            'source_text': c.source_text[:200],
            'severity': c.severity
        } for c in constraints]
        
        # Convert decisions
        decision_list = []
        for d in decisions:
            decision_list.append({
                'id': d.id,
                'decision_type': d.decision_type,
                'summary': d.summary,
                'reasoning': d.reasoning,
                'impact_score': self._safe_float(d.impact_score),
                'confidence_score': self._safe_float(d.confidence_score),
                'urgency_score': self._safe_float(d.urgency_score),
                'action_count': len(d.actions),
                'supporting_gap_count': len(d.supporting_gaps),
                'supporting_constraint_count': len(d.supporting_constraints)
            })
        
        # Top decision summary
        top_decisions = self.decision_generator.get_top_decisions(3)
        if top_decisions:
            top_summary = "; ".join([d.summary for d in top_decisions])
        else:
            top_summary = "No significant decision candidates identified"
        
        # Sheet profiles
        profile_dict = {}
        for name, profile in sheet_profiles.items():
            profile_dict[name] = {
                'row_count': profile.row_count,
                'col_count': profile.col_count,
                'inferred_role': profile.inferred_role.value,
                'confidence': self._safe_float(profile.confidence),
                'has_aggregations': profile.has_aggregations,
                'has_comparisons': profile.has_comparisons,
                'temporal_coverage': profile.temporal_coverage
            }
        
        return AnalysisResult(
            dataset_id=dataset_id,
            analyzed_at=datetime.utcnow().isoformat(),
            sheet_count=len(datasets),
            sheet_roles={n: p.inferred_role.value for n, p in sheet_profiles.items()},
            sheet_profiles=profile_dict,
            entity_count=len(entities),
            entities=entity_list,
            entity_graph=entity_graph,
            gap_count=len(gaps),
            critical_gaps=len([g for g in gaps if g.severity == 'critical']),
            gaps=gap_list,
            plans=plan_list,
            actuals=actual_list,
            constraint_count=len(constraints),
            blocking_constraints=len([c for c in constraints if c.constraint_type in ['blocking', 'deadline']]),
            constraints=constraint_list,
            decision_count=len(decisions),
            decisions=decision_list,
            top_decision_summary=top_summary,
            processing_notes=self.processing_notes
        )
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float for JSON serialization."""
        if value is None:
            return None
        try:
            f = float(value)
            if np.isnan(f) or np.isinf(f):
                return None
            return f
        except:
            return None
    
    def get_context(self) -> DecisionContext:
        """Get the full decision context."""
        return self.context
    
    def to_dict(self, result: AnalysisResult) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return asdict(result)
    
    def to_json(self, result: AnalysisResult) -> str:
        """Convert result to JSON string."""
        return json.dumps(asdict(result), indent=2, default=str)
