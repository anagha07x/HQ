"""Core ontology for industry-agnostic decision intelligence.

This module defines the fundamental concepts that the decision engine
operates on. No domain-specific logic - purely structural abstractions.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
from enum import Enum
from datetime import datetime
import uuid


class SheetRole(Enum):
    """Inferred role of a sheet based on structural signals."""
    MASTER = "master"           # Reference/lookup data (high cardinality key, static)
    TRANSACTIONAL = "transactional"  # Event/fact data (timestamps, amounts)
    PLAN = "plan"               # Forward-looking targets/budgets
    ACTUAL = "actual"           # Historical actuals/results
    SUMMARY = "summary"         # Aggregated/rolled-up data
    COMPARISON = "comparison"   # Plan vs actual or period comparisons
    UNKNOWN = "unknown"


class ColumnSemanticType(Enum):
    """Semantic type inferred from column structure."""
    ENTITY_ID = "entity_id"         # Unique identifier
    ENTITY_NAME = "entity_name"     # Human-readable name
    TEMPORAL = "temporal"           # Date/time values
    QUANTITY = "quantity"           # Numeric counts/amounts
    CURRENCY = "currency"           # Monetary values
    PERCENTAGE = "percentage"       # Ratios/percentages
    STATUS = "status"               # Categorical status
    REMARK = "remark"               # Free-text notes
    DIMENSION = "dimension"         # Categorical grouping
    METRIC = "metric"               # Numeric measure
    UNKNOWN = "unknown"


@dataclass
class Entity:
    """A detected entity (thing that can be tracked/measured)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    canonical_name: str = ""
    source_columns: List[str] = field(default_factory=list)
    source_sheets: List[str] = field(default_factory=list)
    cardinality: int = 0
    is_primary: bool = False
    related_entities: List[str] = field(default_factory=list)
    
    def __hash__(self):
        return hash(self.id)


@dataclass
class Fact:
    """A recorded fact/measurement about an entity."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_id: str = ""
    metric_name: str = ""
    value: Any = None
    timestamp: Optional[datetime] = None
    source_sheet: str = ""
    source_row: int = 0
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    """A planned/target value for an entity-metric pair."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_id: str = ""
    metric_name: str = ""
    target_value: Any = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    source_sheet: str = ""
    confidence: float = 0.0


@dataclass
class Actual:
    """An actual/realized value for an entity-metric pair."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_id: str = ""
    metric_name: str = ""
    actual_value: Any = None
    timestamp: Optional[datetime] = None
    source_sheet: str = ""
    confidence: float = 0.0


@dataclass
class Gap:
    """A detected gap between plan and actual."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_id: str = ""
    metric_name: str = ""
    plan_value: Any = None
    actual_value: Any = None
    absolute_gap: float = 0.0
    percentage_gap: float = 0.0
    direction: str = ""  # "under", "over", "on_target"
    severity: str = ""   # "critical", "warning", "normal"
    period: Optional[str] = None


@dataclass
class Constraint:
    """A detected constraint or limiting factor."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_id: Optional[str] = None
    constraint_type: str = ""  # "capacity", "deadline", "dependency", "resource", "policy"
    description: str = ""
    source_text: str = ""
    source_sheet: str = ""
    source_column: str = ""
    severity: str = "medium"
    extracted_values: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Action:
    """A potential action that could address a gap or constraint."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_type: str = ""  # "increase", "decrease", "reallocate", "investigate", "escalate"
    target_entity_id: str = ""
    target_metric: str = ""
    description: str = ""
    estimated_impact: float = 0.0
    confidence: float = 0.0
    prerequisites: List[str] = field(default_factory=list)
    related_gaps: List[str] = field(default_factory=list)
    related_constraints: List[str] = field(default_factory=list)


@dataclass
class Decision:
    """A decision candidate with supporting evidence."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_type: str = ""  # "approve", "reject", "modify", "investigate", "defer"
    summary: str = ""
    reasoning: str = ""
    actions: List[Action] = field(default_factory=list)
    supporting_gaps: List[Gap] = field(default_factory=list)
    supporting_constraints: List[Constraint] = field(default_factory=list)
    impact_score: float = 0.0
    confidence_score: float = 0.0
    urgency_score: float = 0.0
    evidence: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "candidate"  # "candidate", "accepted", "rejected", "implemented"


@dataclass
class DecisionContext:
    """Full context for decision-making."""
    entities: Dict[str, Entity] = field(default_factory=dict)
    facts: List[Fact] = field(default_factory=list)
    plans: List[Plan] = field(default_factory=list)
    actuals: List[Actual] = field(default_factory=list)
    gaps: List[Gap] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    decisions: List[Decision] = field(default_factory=list)
    entity_graph: Dict[str, Set[str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
