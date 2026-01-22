"""Decision generator - generates decision candidates from analysis.

Synthesizes insights from:
- Gap analysis (plan vs actual)
- Constraints
- Entity relationships
- Statistical patterns

To generate actionable decision candidates with evidence.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid

from .ontology import (
    Decision, Action, Gap, Constraint, Entity,
    DecisionContext, Plan, Actual
)
from .gap_analyzer import GapAnalyzer
from .constraint_extractor import ConstraintExtractor
from .relationship_graph import RelationshipGraph


@dataclass
class DecisionCandidate:
    """A candidate decision before final scoring."""
    decision_type: str
    summary: str
    reasoning: str
    supporting_evidence: List[Dict[str, Any]]
    affected_entities: List[str]
    proposed_actions: List[Dict[str, Any]]
    raw_impact_score: float
    raw_confidence: float
    raw_urgency: float


class DecisionGenerator:
    """Generate decision candidates from analyzed data."""
    
    def __init__(self):
        self.decisions: List[Decision] = []
        self.actions: List[Action] = []
    
    def generate_decisions(
        self,
        context: DecisionContext,
        relationship_graph: RelationshipGraph
    ) -> List[Decision]:
        """Generate decision candidates from analysis context.
        
        Args:
            context: Full decision context with entities, gaps, constraints
            relationship_graph: Entity relationship graph
            
        Returns:
            List of Decision candidates
        """
        candidates = []
        
        # Strategy 1: Gap-driven decisions
        candidates.extend(self._generate_gap_decisions(context))
        
        # Strategy 2: Constraint-driven decisions
        candidates.extend(self._generate_constraint_decisions(context))
        
        # Strategy 3: Pattern-driven decisions (anomalies)
        candidates.extend(self._generate_pattern_decisions(context, relationship_graph))
        
        # Strategy 4: Relationship-driven decisions
        candidates.extend(self._generate_relationship_decisions(context, relationship_graph))
        
        # Score and rank candidates
        scored_decisions = self._score_and_rank(candidates, context)
        
        # Create final Decision objects
        self.decisions = [self._create_decision(c, context) for c in scored_decisions]
        
        return self.decisions
    
    def _generate_gap_decisions(
        self,
        context: DecisionContext
    ) -> List[DecisionCandidate]:
        """Generate decisions based on plan-actual gaps."""
        candidates = []
        
        # Group gaps by entity
        entity_gaps: Dict[str, List[Gap]] = {}
        for gap in context.gaps:
            if gap.entity_id not in entity_gaps:
                entity_gaps[gap.entity_id] = []
            entity_gaps[gap.entity_id].append(gap)
        
        for entity_id, gaps in entity_gaps.items():
            # Critical gaps need immediate attention
            critical_gaps = [g for g in gaps if g.severity == "critical"]
            
            if critical_gaps:
                # Determine dominant direction
                under_count = sum(1 for g in critical_gaps if g.direction == "under")
                over_count = sum(1 for g in critical_gaps if g.direction == "over")
                
                if under_count > over_count:
                    decision_type = "investigate"
                    action_type = "increase"
                    summary = f"Underperformance detected: {len(critical_gaps)} critical gaps"
                else:
                    decision_type = "investigate"
                    action_type = "optimize"
                    summary = f"Overperformance detected: {len(critical_gaps)} critical gaps (verify targets)"
                
                # Calculate total impact
                total_gap = sum(abs(g.absolute_gap) for g in critical_gaps)
                
                candidates.append(DecisionCandidate(
                    decision_type=decision_type,
                    summary=summary,
                    reasoning=self._build_gap_reasoning(critical_gaps),
                    supporting_evidence=[
                        {
                            'type': 'gap',
                            'entity': entity_id,
                            'metric': g.metric_name,
                            'gap_value': g.absolute_gap,
                            'gap_percent': g.percentage_gap,
                            'direction': g.direction
                        }
                        for g in critical_gaps
                    ],
                    affected_entities=[entity_id],
                    proposed_actions=[{
                        'action_type': action_type,
                        'target': entity_id,
                        'metrics': list(set(g.metric_name for g in critical_gaps)),
                        'estimated_impact': total_gap
                    }],
                    raw_impact_score=min(total_gap / 1000, 1.0),  # Normalize
                    raw_confidence=0.8,
                    raw_urgency=0.9 if critical_gaps else 0.5
                ))
            
            # Warning gaps need monitoring
            warning_gaps = [g for g in gaps if g.severity == "warning"]
            if warning_gaps and not critical_gaps:
                candidates.append(DecisionCandidate(
                    decision_type="monitor",
                    summary=f"Potential issues: {len(warning_gaps)} metrics trending off-target",
                    reasoning=self._build_gap_reasoning(warning_gaps),
                    supporting_evidence=[
                        {
                            'type': 'gap',
                            'entity': entity_id,
                            'metric': g.metric_name,
                            'gap_value': g.absolute_gap,
                            'gap_percent': g.percentage_gap
                        }
                        for g in warning_gaps
                    ],
                    affected_entities=[entity_id],
                    proposed_actions=[{
                        'action_type': 'monitor',
                        'target': entity_id,
                        'metrics': list(set(g.metric_name for g in warning_gaps))
                    }],
                    raw_impact_score=0.3,
                    raw_confidence=0.7,
                    raw_urgency=0.4
                ))
        
        return candidates
    
    def _generate_constraint_decisions(
        self,
        context: DecisionContext
    ) -> List[DecisionCandidate]:
        """Generate decisions based on constraints."""
        candidates = []
        
        # Group blocking constraints
        blocking = [c for c in context.constraints if c.constraint_type in ['blocking', 'deadline', 'dependency']]
        
        if blocking:
            # Group by entity
            entity_constraints: Dict[str, List[Constraint]] = {}
            for c in blocking:
                entity_key = c.entity_id or 'global'
                if entity_key not in entity_constraints:
                    entity_constraints[entity_key] = []
                entity_constraints[entity_key].append(c)
            
            for entity_id, constraints in entity_constraints.items():
                # Determine most urgent constraint type
                deadline_constraints = [c for c in constraints if c.constraint_type == 'deadline']
                blocking_constraints = [c for c in constraints if c.constraint_type == 'blocking']
                dependency_constraints = [c for c in constraints if c.constraint_type == 'dependency']
                
                if deadline_constraints:
                    decision_type = "escalate"
                    summary = f"Deadline constraint detected for {entity_id}"
                    urgency = 0.95
                elif blocking_constraints:
                    decision_type = "resolve"
                    summary = f"Blocking issue requires resolution for {entity_id}"
                    urgency = 0.85
                else:
                    decision_type = "sequence"
                    summary = f"Dependency constraint needs sequencing for {entity_id}"
                    urgency = 0.6
                
                candidates.append(DecisionCandidate(
                    decision_type=decision_type,
                    summary=summary,
                    reasoning=self._build_constraint_reasoning(constraints),
                    supporting_evidence=[
                        {
                            'type': 'constraint',
                            'entity': c.entity_id,
                            'constraint_type': c.constraint_type,
                            'description': c.description,
                            'source': c.source_text[:100]
                        }
                        for c in constraints
                    ],
                    affected_entities=[entity_id] if entity_id != 'global' else [],
                    proposed_actions=[{
                        'action_type': 'resolve_constraint',
                        'target': entity_id,
                        'constraint_types': list(set(c.constraint_type for c in constraints))
                    }],
                    raw_impact_score=0.7,
                    raw_confidence=0.6,
                    raw_urgency=urgency
                ))
        
        # Resource constraints
        resource_constraints = [c for c in context.constraints if c.constraint_type == 'resource']
        if resource_constraints:
            candidates.append(DecisionCandidate(
                decision_type="allocate",
                summary=f"Resource constraints detected across {len(resource_constraints)} items",
                reasoning=self._build_constraint_reasoning(resource_constraints),
                supporting_evidence=[
                    {
                        'type': 'constraint',
                        'constraint_type': 'resource',
                        'description': c.description,
                        'values': c.extracted_values
                    }
                    for c in resource_constraints
                ],
                affected_entities=[c.entity_id for c in resource_constraints if c.entity_id],
                proposed_actions=[{
                    'action_type': 'reallocate',
                    'resource_gaps': len(resource_constraints)
                }],
                raw_impact_score=0.5,
                raw_confidence=0.65,
                raw_urgency=0.5
            ))
        
        return candidates
    
    def _generate_pattern_decisions(
        self,
        context: DecisionContext,
        relationship_graph: RelationshipGraph
    ) -> List[DecisionCandidate]:
        """Generate decisions based on statistical patterns."""
        candidates = []
        
        # Analyze gap distribution for systemic issues
        if context.gaps:
            gap_directions = [g.direction for g in context.gaps]
            under_ratio = gap_directions.count("under") / len(gap_directions)
            
            if under_ratio > 0.7:
                # Systemic underperformance
                candidates.append(DecisionCandidate(
                    decision_type="investigate_systemic",
                    summary="Systemic underperformance pattern detected",
                    reasoning=f"{under_ratio*100:.0f}% of tracked metrics are below target, suggesting systemic issue rather than isolated problems",
                    supporting_evidence=[
                        {
                            'type': 'pattern',
                            'pattern': 'systemic_underperformance',
                            'under_ratio': under_ratio,
                            'total_gaps': len(context.gaps)
                        }
                    ],
                    affected_entities=list(set(g.entity_id for g in context.gaps)),
                    proposed_actions=[{
                        'action_type': 'root_cause_analysis',
                        'scope': 'systemic'
                    }],
                    raw_impact_score=0.9,
                    raw_confidence=0.7,
                    raw_urgency=0.8
                ))
            elif under_ratio < 0.3:
                # General overperformance - verify targets
                candidates.append(DecisionCandidate(
                    decision_type="verify_targets",
                    summary="Widespread overperformance suggests target review needed",
                    reasoning=f"{(1-under_ratio)*100:.0f}% of tracked metrics exceed targets - targets may be too conservative",
                    supporting_evidence=[
                        {
                            'type': 'pattern',
                            'pattern': 'systemic_overperformance',
                            'over_ratio': 1 - under_ratio,
                            'total_gaps': len(context.gaps)
                        }
                    ],
                    affected_entities=[],
                    proposed_actions=[{
                        'action_type': 'adjust_targets',
                        'direction': 'increase'
                    }],
                    raw_impact_score=0.5,
                    raw_confidence=0.6,
                    raw_urgency=0.3
                ))
        
        return candidates
    
    def _generate_relationship_decisions(
        self,
        context: DecisionContext,
        relationship_graph: RelationshipGraph
    ) -> List[DecisionCandidate]:
        """Generate decisions based on entity relationships."""
        candidates = []
        
        # Find entities with gaps that affect related entities
        for gap in context.gaps:
            if gap.severity != "critical":
                continue
            
            related = relationship_graph.get_related_entities(gap.entity_id)
            
            if len(related) > 2:
                # This entity's gap might cascade
                candidates.append(DecisionCandidate(
                    decision_type="prioritize",
                    summary=f"High-impact entity '{gap.entity_id}' affects {len(related)} related items",
                    reasoning=f"Gap in '{gap.metric_name}' for entity '{gap.entity_id}' has {len(related)} downstream dependencies",
                    supporting_evidence=[
                        {
                            'type': 'relationship',
                            'source_entity': gap.entity_id,
                            'related_count': len(related),
                            'gap_metric': gap.metric_name,
                            'gap_severity': gap.severity
                        }
                    ],
                    affected_entities=[gap.entity_id] + list(related)[:5],
                    proposed_actions=[{
                        'action_type': 'prioritize_fix',
                        'target': gap.entity_id,
                        'cascade_risk': len(related)
                    }],
                    raw_impact_score=min(len(related) / 10, 1.0),
                    raw_confidence=0.75,
                    raw_urgency=0.85
                ))
        
        return candidates
    
    def _build_gap_reasoning(self, gaps: List[Gap]) -> str:
        """Build reasoning text from gaps."""
        if not gaps:
            return "No gaps detected"
        
        total_gap = sum(abs(g.absolute_gap) for g in gaps)
        avg_percent = np.mean([abs(g.percentage_gap) for g in gaps])
        
        return (
            f"Analysis of {len(gaps)} metric(s) shows deviation from targets. "
            f"Total absolute gap: {total_gap:,.2f}. "
            f"Average percentage gap: {avg_percent:.1f}%. "
            f"Metrics affected: {', '.join(set(g.metric_name for g in gaps))}."
        )
    
    def _build_constraint_reasoning(self, constraints: List[Constraint]) -> str:
        """Build reasoning text from constraints."""
        if not constraints:
            return "No constraints detected"
        
        types = list(set(c.constraint_type for c in constraints))
        
        return (
            f"Detected {len(constraints)} constraint(s) of type(s): {', '.join(types)}. "
            f"These constraints may limit execution or require resolution before proceeding."
        )
    
    def _score_and_rank(
        self,
        candidates: List[DecisionCandidate],
        context: DecisionContext
    ) -> List[DecisionCandidate]:
        """Score and rank decision candidates."""
        if not candidates:
            return []
        
        # Calculate composite scores
        scored = []
        for c in candidates:
            composite_score = (
                0.4 * c.raw_impact_score +
                0.3 * c.raw_urgency +
                0.3 * c.raw_confidence
            )
            scored.append((c, composite_score))
        
        # Sort by composite score
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return [c for c, _ in scored]
    
    def _create_decision(
        self,
        candidate: DecisionCandidate,
        context: DecisionContext
    ) -> Decision:
        """Create a Decision object from a candidate."""
        # Create Action objects
        actions = []
        for action_data in candidate.proposed_actions:
            action = Action(
                action_type=action_data.get('action_type', 'unknown'),
                target_entity_id=action_data.get('target', ''),
                target_metric=action_data.get('metrics', [''])[0] if action_data.get('metrics') else '',
                description=f"{action_data.get('action_type', 'action')} for {action_data.get('target', 'target')}",
                estimated_impact=action_data.get('estimated_impact', 0),
                confidence=candidate.raw_confidence
            )
            actions.append(action)
            self.actions.append(action)
        
        # Collect supporting gaps
        supporting_gaps = [
            gap for gap in context.gaps
            if gap.entity_id in candidate.affected_entities
        ]
        
        # Collect supporting constraints
        supporting_constraints = [
            c for c in context.constraints
            if c.entity_id in candidate.affected_entities or c.entity_id is None
        ]
        
        return Decision(
            decision_type=candidate.decision_type,
            summary=candidate.summary,
            reasoning=candidate.reasoning,
            actions=actions,
            supporting_gaps=supporting_gaps[:10],  # Limit for readability
            supporting_constraints=supporting_constraints[:10],
            impact_score=candidate.raw_impact_score,
            confidence_score=candidate.raw_confidence,
            urgency_score=candidate.raw_urgency,
            evidence={'supporting_evidence': candidate.supporting_evidence}
        )
    
    def get_top_decisions(self, n: int = 5) -> List[Decision]:
        """Get top N decisions by composite score."""
        return sorted(
            self.decisions,
            key=lambda d: (d.urgency_score + d.impact_score + d.confidence_score) / 3,
            reverse=True
        )[:n]
    
    def get_decisions_by_type(self, decision_type: str) -> List[Decision]:
        """Get all decisions of a specific type."""
        return [d for d in self.decisions if d.decision_type == decision_type]
