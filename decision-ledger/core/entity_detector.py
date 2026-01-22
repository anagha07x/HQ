"""Entity detection and linking across sheets.

Detects entities by structural patterns:
- High-cardinality text columns (unique identifiers)
- Shared values across sheets (foreign key relationships)
- Consistent formatting patterns
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict
from dataclasses import dataclass
import re

from .ontology import Entity, ColumnSemanticType
from .sheet_classifier import SheetProfile


@dataclass
class EntityCandidate:
    """A potential entity detected from column analysis."""
    column_name: str
    sheet_name: str
    unique_values: Set[str]
    cardinality: int
    unique_ratio: float
    value_pattern: str  # regex-like pattern of values
    avg_length: float
    is_numeric_id: bool


class EntityDetector:
    """Detect and link entities across sheets."""
    
    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.column_to_entity: Dict[Tuple[str, str], str] = {}  # (sheet, col) -> entity_id
        self.value_index: Dict[str, Set[str]] = {}  # value -> set of entity_ids
    
    def detect_entities(
        self,
        datasets: Dict[str, pd.DataFrame],
        sheet_profiles: Dict[str, SheetProfile]
    ) -> Dict[str, Entity]:
        """Detect entities across all sheets.
        
        Args:
            datasets: Dict mapping sheet names to DataFrames
            sheet_profiles: Sheet classification profiles
            
        Returns:
            Dict mapping entity IDs to Entity objects
        """
        # Step 1: Find entity candidates in each sheet
        candidates = self._find_candidates(datasets, sheet_profiles)
        
        # Step 2: Link candidates across sheets by value overlap
        entity_groups = self._link_candidates(candidates)
        
        # Step 3: Create unified entities
        self.entities = self._create_entities(entity_groups, datasets)
        
        return self.entities
    
    def _find_candidates(
        self,
        datasets: Dict[str, pd.DataFrame],
        sheet_profiles: Dict[str, SheetProfile]
    ) -> List[EntityCandidate]:
        """Find entity candidates in all sheets."""
        candidates = []
        
        for sheet_name, df in datasets.items():
            profile = sheet_profiles.get(sheet_name)
            if not profile:
                continue
            
            for col_profile in profile.column_profiles:
                col_name = col_profile['name']
                
                # Check if this column could be an entity identifier
                if self._is_entity_candidate(col_profile, df[col_name]):
                    candidate = self._create_candidate(
                        col_name, sheet_name, df[col_name]
                    )
                    if candidate:
                        candidates.append(candidate)
        
        return candidates
    
    def _is_entity_candidate(
        self, 
        col_profile: Dict[str, Any], 
        series: pd.Series
    ) -> bool:
        """Check if column could be an entity identifier."""
        semantic_type = col_profile.get('semantic_type')
        
        # Direct entity types
        if semantic_type in [
            ColumnSemanticType.ENTITY_ID,
            ColumnSemanticType.ENTITY_NAME
        ]:
            return True
        
        # Dimension with reasonable cardinality
        if semantic_type == ColumnSemanticType.DIMENSION:
            unique_count = series.nunique()
            if 2 <= unique_count <= len(series) * 0.8:
                return True
        
        # High uniqueness ratio for other types
        unique_ratio = col_profile.get('unique_ratio', 0)
        if unique_ratio > 0.7 and series.nunique() >= 2:
            return True
        
        return False
    
    def _create_candidate(
        self,
        col_name: str,
        sheet_name: str,
        series: pd.Series
    ) -> Optional[EntityCandidate]:
        """Create an entity candidate from a column."""
        non_null = series.dropna()
        
        if non_null.empty:
            return None
        
        # Convert to strings for analysis
        str_values = non_null.astype(str)
        unique_values = set(str_values.unique())
        
        # Skip if too few unique values
        if len(unique_values) < 2:
            return None
        
        # Detect value pattern
        pattern = self._detect_pattern(unique_values)
        
        # Check if numeric IDs
        is_numeric_id = pd.api.types.is_numeric_dtype(series) and \
                       series.nunique() / len(non_null) > 0.9
        
        return EntityCandidate(
            column_name=col_name,
            sheet_name=sheet_name,
            unique_values=unique_values,
            cardinality=len(unique_values),
            unique_ratio=len(unique_values) / len(non_null),
            value_pattern=pattern,
            avg_length=str_values.str.len().mean(),
            is_numeric_id=is_numeric_id
        )
    
    def _detect_pattern(self, values: Set[str]) -> str:
        """Detect structural pattern in values."""
        sample = list(values)[:100]
        
        # Check for common patterns
        patterns = {
            'numeric': r'^\d+$',
            'alpha': r'^[A-Za-z]+$',
            'alphanumeric': r'^[A-Za-z0-9]+$',
            'with_spaces': r'^[\w\s]+$',
            'code_like': r'^[A-Z]{2,4}[-_]?\d+$',
            'mixed': r'.*'
        }
        
        for name, pattern in patterns.items():
            matches = sum(1 for v in sample if re.match(pattern, str(v)))
            if matches / len(sample) > 0.8:
                return name
        
        return 'mixed'
    
    def _link_candidates(
        self,
        candidates: List[EntityCandidate]
    ) -> List[List[EntityCandidate]]:
        """Link candidates that represent the same entity."""
        if not candidates:
            return []
        
        # Build similarity matrix based on value overlap
        n = len(candidates)
        similarity = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i + 1, n):
                sim = self._calculate_similarity(candidates[i], candidates[j])
                similarity[i, j] = sim
                similarity[j, i] = sim
        
        # Group by similarity using simple clustering
        groups = self._cluster_candidates(candidates, similarity)
        
        return groups
    
    def _calculate_similarity(
        self,
        c1: EntityCandidate,
        c2: EntityCandidate
    ) -> float:
        """Calculate similarity between two candidates."""
        # Value overlap (Jaccard similarity)
        overlap = len(c1.unique_values & c2.unique_values)
        union = len(c1.unique_values | c2.unique_values)
        
        if union == 0:
            return 0.0
        
        jaccard = overlap / union
        
        # Pattern similarity
        pattern_match = 1.0 if c1.value_pattern == c2.value_pattern else 0.3
        
        # Cardinality similarity
        card_ratio = min(c1.cardinality, c2.cardinality) / max(c1.cardinality, c2.cardinality)
        
        # Length similarity
        len_ratio = min(c1.avg_length, c2.avg_length) / max(c1.avg_length, c2.avg_length) \
                   if max(c1.avg_length, c2.avg_length) > 0 else 0
        
        # Weighted combination
        similarity = (
            0.5 * jaccard +
            0.2 * pattern_match +
            0.15 * card_ratio +
            0.15 * len_ratio
        )
        
        return similarity
    
    def _cluster_candidates(
        self,
        candidates: List[EntityCandidate],
        similarity: np.ndarray,
        threshold: float = 0.3
    ) -> List[List[EntityCandidate]]:
        """Cluster candidates by similarity."""
        n = len(candidates)
        visited = [False] * n
        groups = []
        
        for i in range(n):
            if visited[i]:
                continue
            
            # Start new group
            group = [candidates[i]]
            visited[i] = True
            
            # Find similar candidates
            for j in range(n):
                if not visited[j] and similarity[i, j] >= threshold:
                    group.append(candidates[j])
                    visited[j] = True
            
            groups.append(group)
        
        return groups
    
    def _create_entities(
        self,
        entity_groups: List[List[EntityCandidate]],
        datasets: Dict[str, pd.DataFrame]
    ) -> Dict[str, Entity]:
        """Create Entity objects from grouped candidates."""
        entities = {}
        
        for group in entity_groups:
            if not group:
                continue
            
            # Find the best representative name
            canonical_name = self._choose_canonical_name(group)
            
            # Collect all source info
            source_columns = list(set(c.column_name for c in group))
            source_sheets = list(set(c.sheet_name for c in group))
            
            # Calculate combined cardinality
            all_values = set()
            for c in group:
                all_values |= c.unique_values
            
            # Determine if this is a primary entity
            is_primary = len(source_sheets) > 1 or any(c.unique_ratio > 0.9 for c in group)
            
            entity = Entity(
                canonical_name=canonical_name,
                source_columns=source_columns,
                source_sheets=source_sheets,
                cardinality=len(all_values),
                is_primary=is_primary
            )
            
            entities[entity.id] = entity
            
            # Update column-to-entity mapping
            for c in group:
                self.column_to_entity[(c.sheet_name, c.column_name)] = entity.id
            
            # Update value index
            for value in all_values:
                if value not in self.value_index:
                    self.value_index[value] = set()
                self.value_index[value].add(entity.id)
        
        return entities
    
    def _choose_canonical_name(self, group: List[EntityCandidate]) -> str:
        """Choose the best name for an entity."""
        # Prefer non-numeric, readable names
        names = []
        for c in group:
            name = c.column_name
            # Score based on readability
            score = 0
            if not c.is_numeric_id:
                score += 2
            if c.value_pattern in ['alpha', 'with_spaces']:
                score += 1
            if c.cardinality > 5:
                score += 1
            names.append((name, score))
        
        # Return highest scored name
        best = max(names, key=lambda x: x[1])
        return best[0]
    
    def get_entity_for_column(
        self, 
        sheet_name: str, 
        column_name: str
    ) -> Optional[Entity]:
        """Get the entity associated with a column."""
        entity_id = self.column_to_entity.get((sheet_name, column_name))
        if entity_id:
            return self.entities.get(entity_id)
        return None
    
    def find_entities_by_value(self, value: str) -> List[Entity]:
        """Find entities that contain a specific value."""
        entity_ids = self.value_index.get(str(value), set())
        return [self.entities[eid] for eid in entity_ids if eid in self.entities]
