"""Decision Grouping Engine - Aggregates decisions into high-level themes.

Groups decisions by:
- Root cause
- Metric
- Entity cluster

Aggregates hundreds of signals into actionable decision themes with drill-down.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import re


@dataclass
class DecisionTheme:
    """A grouped theme containing multiple related decisions."""
    id: str
    theme_name: str
    theme_type: str  # "root_cause", "metric", "entity_cluster"
    headline: str
    summary: str
    decision_count: int
    total_impact: float
    avg_confidence: float
    max_urgency: float
    severity: str
    affected_entities: List[str]
    affected_metrics: List[str]
    decision_ids: List[str]
    representative_decision: Optional[Dict[str, Any]] = None
    drill_down_available: bool = True


@dataclass 
class GroupingSummary:
    """Summary of all decision groupings."""
    total_decisions: int
    total_themes: int
    themes_by_type: Dict[str, int]
    critical_themes: int
    total_impact: float


class DecisionGroupingEngine:
    """Groups decisions into high-level themes for executive consumption."""
    
    def __init__(self):
        self.themes: List[DecisionTheme] = []
        self.theme_index: Dict[str, DecisionTheme] = {}
    
    def group_decisions(
        self,
        decisions: List[Dict[str, Any]],
        entities: List[Dict[str, Any]] = None,
        gaps: List[Dict[str, Any]] = None
    ) -> Tuple[List[DecisionTheme], GroupingSummary]:
        """Group decisions into themes.
        
        Args:
            decisions: List of raw decisions
            entities: Optional list of entities for clustering
            gaps: Optional list of gaps for context
            
        Returns:
            Tuple of (themes list, grouping summary)
        """
        self.themes = []
        self.theme_index = {}
        
        if not decisions:
            return [], GroupingSummary(0, 0, {}, 0, 0.0)
        
        # Group by different dimensions
        root_cause_themes = self._group_by_root_cause(decisions)
        metric_themes = self._group_by_metric(decisions, gaps)
        entity_themes = self._group_by_entity_cluster(decisions, entities)
        
        # Merge and deduplicate themes
        all_themes = self._merge_themes(root_cause_themes, metric_themes, entity_themes)
        
        # Sort by impact
        all_themes.sort(key=lambda t: (t.max_urgency, t.total_impact), reverse=True)
        
        self.themes = all_themes
        self.theme_index = {t.id: t for t in all_themes}
        
        # Generate summary
        summary = self._generate_summary(decisions, all_themes)
        
        return all_themes, summary
    
    def _group_by_root_cause(
        self,
        decisions: List[Dict[str, Any]]
    ) -> List[DecisionTheme]:
        """Group decisions by inferred root cause."""
        themes = []
        
        # Group by decision type (proxy for root cause)
        type_groups: Dict[str, List[Dict]] = defaultdict(list)
        
        for d in decisions:
            dtype = d.get("decision_type", "unknown")
            type_groups[dtype].append(d)
        
        for dtype, group in type_groups.items():
            if len(group) < 2:
                continue  # Skip singleton groups
            
            theme = self._create_theme(
                group=group,
                theme_type="root_cause",
                theme_name=self._get_root_cause_name(dtype),
                id_prefix=f"rc_{dtype}"
            )
            themes.append(theme)
        
        return themes
    
    def _group_by_metric(
        self,
        decisions: List[Dict[str, Any]],
        gaps: List[Dict[str, Any]] = None
    ) -> List[DecisionTheme]:
        """Group decisions by affected metrics."""
        themes = []
        
        if not gaps:
            return themes
        
        # Build decision-to-metric mapping
        metric_decisions: Dict[str, List[Dict]] = defaultdict(list)
        
        # Extract metrics from gap data
        gap_metrics = set()
        for g in gaps:
            metric = g.get("metric_name", "").lower()
            if metric:
                gap_metrics.add(metric)
        
        # Group decisions that mention similar metrics in their summary
        for d in decisions:
            summary = d.get("summary", "").lower()
            reasoning = d.get("reasoning", "").lower()
            
            matched_metrics = set()
            for metric in gap_metrics:
                metric_words = set(metric.split("_"))
                if any(word in summary or word in reasoning for word in metric_words if len(word) > 2):
                    matched_metrics.add(metric)
            
            # Also extract metrics from evidence
            evidence = d.get("evidence", {}).get("supporting_evidence", [])
            for ev in evidence:
                if ev.get("type") == "gap":
                    m = ev.get("metric", "")
                    if m:
                        matched_metrics.add(m.lower())
            
            for metric in matched_metrics:
                metric_decisions[metric].append(d)
        
        # Create themes for metrics with multiple decisions
        for metric, group in metric_decisions.items():
            if len(group) < 2:
                continue
            
            # Deduplicate by decision id
            seen_ids = set()
            unique_group = []
            for d in group:
                if d.get("id") not in seen_ids:
                    seen_ids.add(d.get("id"))
                    unique_group.append(d)
            
            if len(unique_group) < 2:
                continue
            
            theme = self._create_theme(
                group=unique_group,
                theme_type="metric",
                theme_name=self._format_metric_name(metric),
                id_prefix=f"metric_{metric[:20]}"
            )
            themes.append(theme)
        
        return themes
    
    def _group_by_entity_cluster(
        self,
        decisions: List[Dict[str, Any]],
        entities: List[Dict[str, Any]] = None
    ) -> List[DecisionTheme]:
        """Group decisions by entity clusters."""
        themes = []
        
        if not entities:
            return themes
        
        # Build entity name set
        entity_names = set()
        for e in entities:
            name = e.get("canonical_name", "").lower()
            if name:
                entity_names.add(name)
        
        # Group decisions by mentioned entities
        entity_decisions: Dict[str, List[Dict]] = defaultdict(list)
        
        for d in decisions:
            summary = d.get("summary", "")
            
            for entity_name in entity_names:
                # Check if entity is mentioned
                if entity_name.lower() in summary.lower():
                    entity_decisions[entity_name].append(d)
            
            # Also check evidence
            evidence = d.get("evidence", {}).get("supporting_evidence", [])
            for ev in evidence:
                entity = ev.get("entity", "")
                if entity:
                    entity_lower = entity.lower()
                    for ename in entity_names:
                        if ename in entity_lower or entity_lower in ename:
                            entity_decisions[ename].append(d)
        
        # Create themes for entities with multiple decisions
        for entity, group in entity_decisions.items():
            if len(group) < 2:
                continue
            
            # Deduplicate
            seen_ids = set()
            unique_group = []
            for d in group:
                if d.get("id") not in seen_ids:
                    seen_ids.add(d.get("id"))
                    unique_group.append(d)
            
            if len(unique_group) < 2:
                continue
            
            theme = self._create_theme(
                group=unique_group,
                theme_type="entity_cluster",
                theme_name=f"{entity.title()} Portfolio",
                id_prefix=f"entity_{entity[:20]}"
            )
            themes.append(theme)
        
        return themes
    
    def _create_theme(
        self,
        group: List[Dict[str, Any]],
        theme_type: str,
        theme_name: str,
        id_prefix: str
    ) -> DecisionTheme:
        """Create a theme from a group of decisions."""
        import hashlib
        
        # Generate unique ID
        decision_ids = [d.get("id", "") for d in group]
        id_hash = hashlib.md5("".join(sorted(decision_ids)).encode()).hexdigest()[:8]
        theme_id = f"{id_prefix}_{id_hash}"
        
        # Calculate aggregate metrics
        total_impact = sum(d.get("impact_score", 0) for d in group)
        avg_confidence = sum(d.get("confidence_score", 0) for d in group) / len(group) if group else 0
        max_urgency = max(d.get("urgency_score", 0) for d in group) if group else 0
        
        # Collect affected entities and metrics
        affected_entities = set()
        affected_metrics = set()
        
        for d in group:
            summary = d.get("summary", "")
            # Extract entities from summary (simplified)
            words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', summary)
            affected_entities.update(words[:3])
            
            evidence = d.get("evidence", {}).get("supporting_evidence", [])
            for ev in evidence:
                if ev.get("entity"):
                    affected_entities.add(str(ev.get("entity"))[:30])
                if ev.get("metric"):
                    affected_metrics.add(str(ev.get("metric")))
        
        # Determine severity
        severity = self._calculate_theme_severity(total_impact / len(group), max_urgency)
        
        # Generate headline and summary
        headline = self._generate_theme_headline(theme_type, theme_name, len(group), severity)
        summary = self._generate_theme_summary(theme_type, theme_name, group, severity)
        
        # Get representative decision (highest impact)
        representative = max(group, key=lambda d: d.get("impact_score", 0))
        
        return DecisionTheme(
            id=theme_id,
            theme_name=theme_name,
            theme_type=theme_type,
            headline=headline,
            summary=summary,
            decision_count=len(group),
            total_impact=total_impact,
            avg_confidence=avg_confidence,
            max_urgency=max_urgency,
            severity=severity,
            affected_entities=list(affected_entities)[:10],
            affected_metrics=list(affected_metrics)[:10],
            decision_ids=decision_ids,
            representative_decision=representative,
            drill_down_available=True
        )
    
    def _merge_themes(
        self,
        *theme_lists: List[DecisionTheme]
    ) -> List[DecisionTheme]:
        """Merge theme lists, removing duplicates."""
        all_themes = []
        seen_decision_sets = set()
        
        for themes in theme_lists:
            for theme in themes:
                # Create a signature from decision IDs
                decision_set = frozenset(theme.decision_ids)
                
                # Skip if we've seen very similar themes (>80% overlap)
                is_duplicate = False
                for seen_set in seen_decision_sets:
                    overlap = len(decision_set & seen_set) / max(len(decision_set), 1)
                    if overlap > 0.8:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    all_themes.append(theme)
                    seen_decision_sets.add(decision_set)
        
        return all_themes
    
    def _get_root_cause_name(self, decision_type: str) -> str:
        """Get human-readable root cause name."""
        names = {
            "investigate": "Performance Investigation Required",
            "investigate_systemic": "Systemic Issues Detected",
            "escalate": "Escalation Required",
            "monitor": "Active Monitoring Needed",
            "resolve": "Resolution Actions Pending",
            "prioritize": "Prioritization Decisions",
            "allocate": "Resource Allocation Issues",
            "sequence": "Dependency Management",
            "verify_targets": "Target Calibration Review"
        }
        return names.get(decision_type, decision_type.replace("_", " ").title())
    
    def _format_metric_name(self, metric: str) -> str:
        """Format metric name for display."""
        return metric.replace("_", " ").title()
    
    def _calculate_theme_severity(self, avg_impact: float, max_urgency: float) -> str:
        """Calculate theme severity."""
        score = (avg_impact + max_urgency) / 2
        if score >= 0.7:
            return "critical"
        elif score >= 0.4:
            return "warning"
        return "normal"
    
    def _generate_theme_headline(
        self,
        theme_type: str,
        theme_name: str,
        count: int,
        severity: str
    ) -> str:
        """Generate theme headline."""
        severity_prefix = ""
        if severity == "critical":
            severity_prefix = "Critical: "
        elif severity == "warning":
            severity_prefix = "Attention: "
        
        return f"{severity_prefix}{theme_name} ({count} Decisions)"
    
    def _generate_theme_summary(
        self,
        theme_type: str,
        theme_name: str,
        group: List[Dict],
        severity: str
    ) -> str:
        """Generate theme summary."""
        count = len(group)
        
        if theme_type == "root_cause":
            return (
                f"{count} related decisions identified with common root cause pattern. "
                f"Addressing the underlying issue may resolve multiple findings simultaneously."
            )
        elif theme_type == "metric":
            return (
                f"{count} decisions relate to {theme_name} performance. "
                f"Consider a focused review of this metric area."
            )
        elif theme_type == "entity_cluster":
            return (
                f"{count} decisions affect {theme_name}. "
                f"A coordinated response may be more effective than individual actions."
            )
        else:
            return f"{count} related decisions grouped for coordinated review."
    
    def _generate_summary(
        self,
        decisions: List[Dict],
        themes: List[DecisionTheme]
    ) -> GroupingSummary:
        """Generate overall grouping summary."""
        themes_by_type = defaultdict(int)
        for theme in themes:
            themes_by_type[theme.theme_type] += 1
        
        critical_count = sum(1 for t in themes if t.severity == "critical")
        total_impact = sum(t.total_impact for t in themes)
        
        return GroupingSummary(
            total_decisions=len(decisions),
            total_themes=len(themes),
            themes_by_type=dict(themes_by_type),
            critical_themes=critical_count,
            total_impact=total_impact
        )
    
    def get_theme(self, theme_id: str) -> Optional[DecisionTheme]:
        """Get a specific theme by ID."""
        return self.theme_index.get(theme_id)
    
    def get_decisions_for_theme(
        self,
        theme_id: str,
        all_decisions: List[Dict]
    ) -> List[Dict]:
        """Get all decisions belonging to a theme."""
        theme = self.get_theme(theme_id)
        if not theme:
            return []
        
        decision_ids = set(theme.decision_ids)
        return [d for d in all_decisions if d.get("id") in decision_ids]
    
    def to_dict(self, theme: DecisionTheme) -> Dict[str, Any]:
        """Convert theme to dictionary."""
        return asdict(theme)
    
    def themes_to_dict(self) -> List[Dict[str, Any]]:
        """Convert all themes to list of dictionaries."""
        return [self.to_dict(t) for t in self.themes]
