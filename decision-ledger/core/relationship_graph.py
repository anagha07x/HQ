"""Entity relationship graph builder.

Builds a graph of relationships between entities based on:
- Shared values across sheets
- Co-occurrence patterns
- Structural dependencies
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict
from dataclasses import dataclass

from .ontology import Entity, DecisionContext
from .entity_detector import EntityDetector
from .sheet_classifier import SheetProfile, SheetRole


@dataclass
class Relationship:
    """A relationship between two entities."""
    source_entity_id: str
    target_entity_id: str
    relationship_type: str  # "references", "aggregates", "derives", "co-occurs"
    strength: float  # 0-1 confidence
    evidence: Dict[str, Any]


class RelationshipGraph:
    """Build and query entity relationships."""
    
    def __init__(self):
        self.relationships: List[Relationship] = []
        self.adjacency: Dict[str, Set[str]] = defaultdict(set)
        self.relationship_index: Dict[Tuple[str, str], Relationship] = {}
    
    def build_graph(
        self,
        datasets: Dict[str, pd.DataFrame],
        entities: Dict[str, Entity],
        entity_detector: EntityDetector,
        sheet_profiles: Dict[str, SheetProfile]
    ) -> Dict[str, Set[str]]:
        """Build entity relationship graph.
        
        Args:
            datasets: Sheet data
            entities: Detected entities
            entity_detector: Entity detector with column mappings
            sheet_profiles: Sheet classifications
            
        Returns:
            Adjacency dict mapping entity_id to related entity_ids
        """
        # Find relationships through different mechanisms
        self._find_co_occurrence_relationships(
            datasets, entities, entity_detector, sheet_profiles
        )
        self._find_reference_relationships(
            datasets, entities, entity_detector
        )
        self._find_aggregation_relationships(
            datasets, entities, sheet_profiles
        )
        
        # Update entity objects with relationships
        for entity in entities.values():
            entity.related_entities = list(self.adjacency[entity.id])
        
        return dict(self.adjacency)
    
    def _find_co_occurrence_relationships(
        self,
        datasets: Dict[str, pd.DataFrame],
        entities: Dict[str, Entity],
        entity_detector: EntityDetector,
        sheet_profiles: Dict[str, SheetProfile]
    ):
        """Find entities that co-occur in the same rows."""
        for sheet_name, df in datasets.items():
            # Find all entity columns in this sheet
            entity_columns = []
            for col in df.columns:
                entity = entity_detector.get_entity_for_column(sheet_name, str(col))
                if entity:
                    entity_columns.append((str(col), entity))
            
            # Find co-occurring entities
            for i, (col1, entity1) in enumerate(entity_columns):
                for col2, entity2 in entity_columns[i+1:]:
                    if entity1.id == entity2.id:
                        continue
                    
                    # Calculate co-occurrence strength
                    both_present = df[[col1, col2]].dropna().shape[0]
                    total = df.shape[0]
                    
                    if total > 0 and both_present / total > 0.5:
                        strength = both_present / total
                        
                        rel = Relationship(
                            source_entity_id=entity1.id,
                            target_entity_id=entity2.id,
                            relationship_type="co-occurs",
                            strength=strength,
                            evidence={
                                'sheet': sheet_name,
                                'source_col': col1,
                                'target_col': col2,
                                'co_occurrence_count': both_present
                            }
                        )
                        self._add_relationship(rel)
    
    def _find_reference_relationships(
        self,
        datasets: Dict[str, pd.DataFrame],
        entities: Dict[str, Entity],
        entity_detector: EntityDetector
    ):
        """Find foreign key-like references between entities."""
        # For each entity, check if its values appear in other sheets
        for entity in entities.values():
            if len(entity.source_sheets) < 2:
                continue
            
            # This entity spans multiple sheets - likely a reference
            primary_sheet = entity.source_sheets[0]
            
            for other_sheet in entity.source_sheets[1:]:
                if primary_sheet == other_sheet:
                    continue
                
                # Find other entities in the other sheet
                other_df = datasets.get(other_sheet)
                if other_df is None:
                    continue
                
                for col in other_df.columns:
                    other_entity = entity_detector.get_entity_for_column(
                        other_sheet, str(col)
                    )
                    if other_entity and other_entity.id != entity.id:
                        # Check value overlap
                        rel = Relationship(
                            source_entity_id=entity.id,
                            target_entity_id=other_entity.id,
                            relationship_type="references",
                            strength=0.7,
                            evidence={
                                'mechanism': 'cross_sheet_reference',
                                'sheets': [primary_sheet, other_sheet]
                            }
                        )
                        self._add_relationship(rel)
    
    def _find_aggregation_relationships(
        self,
        datasets: Dict[str, pd.DataFrame],
        entities: Dict[str, Entity],
        sheet_profiles: Dict[str, SheetProfile]
    ):
        """Find aggregation relationships (summary sheets)."""
        summary_sheets = [
            name for name, profile in sheet_profiles.items()
            if profile.inferred_role == SheetRole.SUMMARY
        ]
        
        detail_sheets = [
            name for name, profile in sheet_profiles.items()
            if profile.inferred_role in [
                SheetRole.TRANSACTIONAL, 
                SheetRole.ACTUAL,
                SheetRole.PLAN
            ]
        ]
        
        # Check if summary sheets aggregate detail sheets
        for summary_sheet in summary_sheets:
            summary_df = datasets.get(summary_sheet)
            if summary_df is None:
                continue
            
            for detail_sheet in detail_sheets:
                detail_df = datasets.get(detail_sheet)
                if detail_df is None:
                    continue
                
                # Check for numeric columns that could be aggregated
                summary_numeric = summary_df.select_dtypes(include=[np.number]).columns
                detail_numeric = detail_df.select_dtypes(include=[np.number]).columns
                
                # Find matching aggregations
                for sum_col in summary_numeric:
                    for det_col in detail_numeric:
                        detail_sum = detail_df[det_col].sum()
                        summary_vals = summary_df[sum_col].dropna()
                        
                        if not summary_vals.empty:
                            # Check if any summary value matches detail sum
                            for val in summary_vals:
                                if abs(val - detail_sum) < 0.01 * abs(detail_sum) if detail_sum != 0 else val == 0:
                                    # Found aggregation relationship
                                    rel = Relationship(
                                        source_entity_id=f"sheet:{detail_sheet}",
                                        target_entity_id=f"sheet:{summary_sheet}",
                                        relationship_type="aggregates",
                                        strength=0.9,
                                        evidence={
                                            'detail_column': str(det_col),
                                            'summary_column': str(sum_col),
                                            'aggregation_type': 'sum'
                                        }
                                    )
                                    self._add_relationship(rel)
                                    break
    
    def _add_relationship(self, rel: Relationship):
        """Add a relationship to the graph."""
        key = (rel.source_entity_id, rel.target_entity_id)
        
        # Update or add relationship
        existing = self.relationship_index.get(key)
        if existing:
            # Merge - keep higher strength
            if rel.strength > existing.strength:
                self.relationship_index[key] = rel
        else:
            self.relationships.append(rel)
            self.relationship_index[key] = rel
        
        # Update adjacency
        self.adjacency[rel.source_entity_id].add(rel.target_entity_id)
        self.adjacency[rel.target_entity_id].add(rel.source_entity_id)
    
    def get_related_entities(self, entity_id: str) -> Set[str]:
        """Get all entities related to a given entity."""
        return self.adjacency.get(entity_id, set())
    
    def get_relationship(
        self, 
        source_id: str, 
        target_id: str
    ) -> Optional[Relationship]:
        """Get relationship between two entities."""
        return self.relationship_index.get((source_id, target_id)) or \
               self.relationship_index.get((target_id, source_id))
    
    def get_relationship_chain(
        self,
        start_entity_id: str,
        max_depth: int = 3
    ) -> Dict[str, int]:
        """Get all entities reachable from start within max_depth."""
        visited = {start_entity_id: 0}
        frontier = [start_entity_id]
        
        for depth in range(1, max_depth + 1):
            next_frontier = []
            for entity_id in frontier:
                for related_id in self.adjacency.get(entity_id, set()):
                    if related_id not in visited:
                        visited[related_id] = depth
                        next_frontier.append(related_id)
            frontier = next_frontier
        
        return visited
