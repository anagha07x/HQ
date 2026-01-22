"""Constraint extractor - extracts constraints from text fields.

Analyzes remark, status, and note columns to identify:
- Capacity constraints
- Deadline constraints
- Dependency constraints
- Resource constraints
- Policy constraints
"""

import pandas as pd
import numpy as np
import re
from typing import Dict, List, Tuple, Any, Optional, Set
from dataclasses import dataclass
from collections import Counter

from .ontology import Constraint, ColumnSemanticType
from .sheet_classifier import SheetProfile
from .entity_detector import EntityDetector


@dataclass
class TextPattern:
    """A detected pattern in text data."""
    pattern_type: str
    matched_text: str
    extracted_values: Dict[str, Any]
    confidence: float


class ConstraintExtractor:
    """Extract constraints from text fields using pattern analysis."""
    
    def __init__(self):
        self.constraints: List[Constraint] = []
        self._status_patterns: Dict[str, str] = {}  # value -> constraint type
    
    def extract_constraints(
        self,
        datasets: Dict[str, pd.DataFrame],
        entities: Dict[str, 'Entity'],
        entity_detector: EntityDetector,
        sheet_profiles: Dict[str, SheetProfile]
    ) -> List[Constraint]:
        """Extract constraints from all text fields.
        
        Args:
            datasets: Sheet data
            entities: Detected entities
            entity_detector: Entity detector
            sheet_profiles: Sheet classifications
            
        Returns:
            List of extracted constraints
        """
        for sheet_name, df in datasets.items():
            profile = sheet_profiles.get(sheet_name)
            if not profile:
                continue
            
            # Find text columns that might contain constraints
            constraint_columns = self._identify_constraint_columns(df, profile)
            
            for col_name, col_type in constraint_columns:
                self._extract_from_column(
                    df, col_name, col_type, sheet_name,
                    entities, entity_detector
                )
        
        return self.constraints
    
    def _identify_constraint_columns(
        self,
        df: pd.DataFrame,
        profile: SheetProfile
    ) -> List[Tuple[str, str]]:
        """Identify columns likely to contain constraints."""
        constraint_cols = []
        
        for col_profile in profile.column_profiles:
            col_name = col_profile['name']
            semantic_type = col_profile.get('semantic_type')
            
            # Status columns often contain constraint info
            if semantic_type == ColumnSemanticType.STATUS:
                constraint_cols.append((col_name, 'status'))
            
            # Remark columns contain free-text constraints
            elif semantic_type == ColumnSemanticType.REMARK:
                constraint_cols.append((col_name, 'remark'))
            
            # Check for low-cardinality text columns
            elif df[col_name].dtype == 'object':
                unique_ratio = col_profile.get('unique_ratio', 1)
                if unique_ratio < 0.3:
                    # Low cardinality text - might be status/category
                    constraint_cols.append((col_name, 'category'))
        
        return constraint_cols
    
    def _extract_from_column(
        self,
        df: pd.DataFrame,
        col_name: str,
        col_type: str,
        sheet_name: str,
        entities: Dict[str, 'Entity'],
        entity_detector: EntityDetector
    ):
        """Extract constraints from a specific column."""
        if col_type == 'status':
            self._extract_from_status(df, col_name, sheet_name, entity_detector)
        elif col_type == 'remark':
            self._extract_from_remarks(df, col_name, sheet_name, entity_detector)
        elif col_type == 'category':
            self._extract_from_category(df, col_name, sheet_name, entity_detector)
    
    def _extract_from_status(
        self,
        df: pd.DataFrame,
        col_name: str,
        sheet_name: str,
        entity_detector: EntityDetector
    ):
        """Extract constraints from status columns."""
        # Analyze status value distribution
        status_counts = df[col_name].value_counts()
        
        # Identify blocking/constraining statuses
        blocking_patterns = self._identify_blocking_statuses(status_counts)
        
        for idx, row in df.iterrows():
            status_val = row.get(col_name)
            if pd.isna(status_val):
                continue
            
            status_str = str(status_val).strip().lower()
            
            # Check if this status indicates a constraint
            constraint_type = blocking_patterns.get(status_str)
            if constraint_type:
                # Find entity for this row
                entity_id = self._get_row_entity(df, idx, sheet_name, entity_detector)
                
                constraint = Constraint(
                    entity_id=entity_id,
                    constraint_type=constraint_type,
                    description=f"Status indicates {constraint_type}: {status_val}",
                    source_text=str(status_val),
                    source_sheet=sheet_name,
                    source_column=col_name,
                    severity=self._severity_from_constraint_type(constraint_type),
                    extracted_values={'status': str(status_val)}
                )
                self.constraints.append(constraint)
    
    def _extract_from_remarks(
        self,
        df: pd.DataFrame,
        col_name: str,
        sheet_name: str,
        entity_detector: EntityDetector
    ):
        """Extract constraints from free-text remark columns."""
        for idx, row in df.iterrows():
            remark = row.get(col_name)
            if pd.isna(remark):
                continue
            
            remark_str = str(remark).strip()
            if len(remark_str) < 3:
                continue
            
            # Extract patterns from remark text
            patterns = self._analyze_remark_text(remark_str)
            
            entity_id = self._get_row_entity(df, idx, sheet_name, entity_detector)
            
            for pattern in patterns:
                constraint = Constraint(
                    entity_id=entity_id,
                    constraint_type=pattern.pattern_type,
                    description=f"Extracted from remark: {pattern.matched_text[:100]}",
                    source_text=remark_str,
                    source_sheet=sheet_name,
                    source_column=col_name,
                    severity=self._determine_severity(pattern),
                    extracted_values=pattern.extracted_values
                )
                self.constraints.append(constraint)
    
    def _extract_from_category(
        self,
        df: pd.DataFrame,
        col_name: str,
        sheet_name: str,
        entity_detector: EntityDetector
    ):
        """Extract constraints from category/dimension columns."""
        # Look for categories that might indicate constraints
        value_counts = df[col_name].value_counts()
        
        # Minority categories often indicate exceptions/constraints
        total = value_counts.sum()
        
        for value, count in value_counts.items():
            proportion = count / total
            
            # Very rare category might indicate special constraint
            if proportion < 0.05 and count >= 1:
                # Find rows with this category
                mask = df[col_name] == value
                
                for idx in df[mask].index:
                    entity_id = self._get_row_entity(df, idx, sheet_name, entity_detector)
                    
                    constraint = Constraint(
                        entity_id=entity_id,
                        constraint_type="exception",
                        description=f"Rare category value: {value}",
                        source_text=str(value),
                        source_sheet=sheet_name,
                        source_column=col_name,
                        severity="medium",
                        extracted_values={'category': str(value), 'proportion': proportion}
                    )
                    self.constraints.append(constraint)
    
    def _identify_blocking_statuses(
        self,
        status_counts: pd.Series
    ) -> Dict[str, str]:
        """Identify which status values indicate blocking conditions."""
        blocking = {}
        
        # Patterns that suggest blocking/constraint status
        # These are structural patterns, not domain-specific keywords
        
        total = status_counts.sum()
        
        for status, count in status_counts.items():
            status_lower = str(status).strip().lower()
            proportion = count / total
            
            # Minority statuses more likely to be constraints
            if proportion < 0.3:
                # Structural analysis of the value
                constraint_type = self._classify_status_structurally(status_lower, proportion)
                if constraint_type:
                    blocking[status_lower] = constraint_type
        
        return blocking
    
    def _classify_status_structurally(
        self,
        status: str,
        proportion: float
    ) -> Optional[str]:
        """Classify a status value structurally."""
        # Very rare status (< 5%) more likely to be an issue
        if proportion < 0.05:
            # Check for negation patterns
            if self._has_negation_pattern(status):
                return "blocking"
            return "exception"
        
        # Moderate minority (5-20%) could be in-progress or pending
        if proportion < 0.2:
            if self._has_process_pattern(status):
                return "in_progress"
            return "dependency"
        
        return None
    
    def _has_negation_pattern(self, text: str) -> bool:
        """Check for structural negation patterns."""
        # Look for structural negation (not keyword-based)
        # Examples: "not X", "un-X", "X-less", "no X"
        
        # Starts with negation prefixes
        if re.match(r'^(un|non|not?|dis|im|in)\b', text):
            return True
        
        # Contains negation words
        if re.search(r'\b(not|no|none|never|cannot|cant|won\'t|wouldn\'t)\b', text):
            return True
        
        return False
    
    def _has_process_pattern(self, text: str) -> bool:
        """Check for in-process/pending patterns."""
        # Look for -ing endings or process indicators
        if re.search(r'ing\b', text):
            return True
        
        # Ellipsis or continuation markers
        if '...' in text:
            return True
        
        return False
    
    def _analyze_remark_text(self, text: str) -> List[TextPattern]:
        """Analyze remark text for constraint patterns."""
        patterns = []
        text_lower = text.lower()
        
        # Pattern 1: Numeric thresholds/limits
        limit_matches = re.findall(
            r'(\d+(?:\.\d+)?)\s*(%|units?|days?|weeks?|months?|hours?)',
            text_lower
        )
        for value, unit in limit_matches:
            patterns.append(TextPattern(
                pattern_type="capacity",
                matched_text=f"{value} {unit}",
                extracted_values={'value': float(value), 'unit': unit},
                confidence=0.7
            ))
        
        # Pattern 2: Date references
        date_matches = re.findall(
            r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
            text
        )
        for date_str in date_matches:
            patterns.append(TextPattern(
                pattern_type="deadline",
                matched_text=date_str,
                extracted_values={'date': date_str},
                confidence=0.6
            ))
        
        # Pattern 3: Dependency indicators (structural)
        # Looking for "X then Y" or "after X" or "requires X" patterns
        if re.search(r'\b(then|after|before|requires|needs|depends)\b', text_lower):
            patterns.append(TextPattern(
                pattern_type="dependency",
                matched_text=text[:100],
                extracted_values={'full_text': text},
                confidence=0.5
            ))
        
        # Pattern 4: Negation (issues/blockers)
        if self._has_negation_pattern(text_lower):
            patterns.append(TextPattern(
                pattern_type="blocking",
                matched_text=text[:100],
                extracted_values={'full_text': text},
                confidence=0.6
            ))
        
        # Pattern 5: Quantity shortages
        shortage_match = re.search(
            r'(\d+(?:\.\d+)?)\s*(short|missing|lacking|needed)',
            text_lower
        )
        if shortage_match:
            patterns.append(TextPattern(
                pattern_type="resource",
                matched_text=shortage_match.group(0),
                extracted_values={
                    'quantity': float(shortage_match.group(1)),
                    'type': shortage_match.group(2)
                },
                confidence=0.7
            ))
        
        return patterns
    
    def _get_row_entity(
        self,
        df: pd.DataFrame,
        idx: Any,
        sheet_name: str,
        entity_detector: EntityDetector
    ) -> Optional[str]:
        """Get the entity ID for a row."""
        for col in df.columns:
            entity = entity_detector.get_entity_for_column(sheet_name, str(col))
            if entity and entity.is_primary:
                value = df.loc[idx, col]
                if not pd.isna(value):
                    return str(value)
        return None
    
    def _severity_from_constraint_type(self, constraint_type: str) -> str:
        """Determine severity from constraint type."""
        high_severity = {'blocking', 'deadline', 'critical'}
        medium_severity = {'dependency', 'resource', 'capacity'}
        
        if constraint_type in high_severity:
            return "high"
        elif constraint_type in medium_severity:
            return "medium"
        return "low"
    
    def _determine_severity(self, pattern: TextPattern) -> str:
        """Determine severity from a text pattern."""
        if pattern.confidence > 0.7:
            return self._severity_from_constraint_type(pattern.pattern_type)
        return "low"
    
    def get_constraints_by_type(self, constraint_type: str) -> List[Constraint]:
        """Get all constraints of a specific type."""
        return [c for c in self.constraints if c.constraint_type == constraint_type]
    
    def get_constraints_by_entity(self, entity_id: str) -> List[Constraint]:
        """Get all constraints for a specific entity."""
        return [c for c in self.constraints if c.entity_id == entity_id]
    
    def get_blocking_constraints(self) -> List[Constraint]:
        """Get all blocking constraints."""
        blocking_types = {'blocking', 'deadline', 'dependency'}
        return [c for c in self.constraints if c.constraint_type in blocking_types]
