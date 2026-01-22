"""Decision Explainer - Converts technical outputs to executive-readable language.

Produces human-first explanations with:
- Headline
- Plain English summary
- Business impact
- Root cause explanation
- Recommended action
- Confidence rationale
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import math

from .vocabulary_adapter import IndustryVocabularyAdapter


@dataclass
class ExecutiveExplanation:
    """Executive-readable explanation of a decision or finding."""
    headline: str
    summary: str
    business_impact: str
    root_cause: str
    recommended_action: str
    confidence_rationale: str
    severity: str
    impact_value: Optional[float] = None
    confidence_score: Optional[float] = None
    urgency_score: Optional[float] = None
    supporting_data: Optional[Dict[str, Any]] = None


@dataclass
class GapExplanation:
    """Executive-readable explanation of a gap."""
    headline: str
    summary: str
    business_impact: str
    root_cause: str
    recommended_action: str
    metric_context: str
    severity: str
    plan_value: Optional[float] = None
    actual_value: Optional[float] = None
    variance_value: Optional[float] = None
    variance_percent: Optional[float] = None


@dataclass
class EntityExplanation:
    """Executive-readable explanation of an entity."""
    name: str
    description: str
    significance: str
    data_coverage: str
    cardinality: int
    relationship_summary: str


class DecisionExplainer:
    """Converts technical decision intelligence outputs to executive language."""
    
    def __init__(self, industry: str = "generic"):
        """Initialize with industry vocabulary.
        
        Args:
            industry: Target industry for vocabulary adaptation
        """
        self.vocab = IndustryVocabularyAdapter(industry)
        self.industry = industry
    
    def explain_decision(self, decision: Dict[str, Any]) -> ExecutiveExplanation:
        """Convert a raw decision to executive explanation.
        
        Args:
            decision: Raw decision dict from decision generator
            
        Returns:
            ExecutiveExplanation with human-readable content
        """
        decision_type = decision.get("decision_type", "unknown")
        summary = decision.get("summary", "")
        reasoning = decision.get("reasoning", "")
        impact_score = decision.get("impact_score", 0)
        confidence_score = decision.get("confidence_score", 0)
        urgency_score = decision.get("urgency_score", 0)
        gap_count = decision.get("supporting_gap_count", 0)
        constraint_count = decision.get("supporting_constraint_count", 0)
        
        # Generate headline
        headline = self._generate_decision_headline(decision_type, summary, impact_score)
        
        # Generate plain English summary
        plain_summary = self._generate_decision_summary(
            decision_type, summary, gap_count, constraint_count
        )
        
        # Generate business impact
        business_impact = self._generate_business_impact(
            decision_type, impact_score, gap_count
        )
        
        # Generate root cause
        root_cause = self._generate_root_cause(decision_type, reasoning)
        
        # Generate recommended action
        recommended_action = self._generate_recommended_action(
            decision_type, urgency_score
        )
        
        # Generate confidence rationale
        confidence_rationale = self._generate_confidence_rationale(
            confidence_score, gap_count, constraint_count
        )
        
        # Determine severity
        severity = self._score_to_severity(impact_score, urgency_score)
        
        return ExecutiveExplanation(
            headline=headline,
            summary=plain_summary,
            business_impact=business_impact,
            root_cause=root_cause,
            recommended_action=recommended_action,
            confidence_rationale=confidence_rationale,
            severity=severity,
            impact_value=impact_score,
            confidence_score=confidence_score,
            urgency_score=urgency_score,
            supporting_data={
                "gap_count": gap_count,
                "constraint_count": constraint_count,
                "decision_type": decision_type
            }
        )
    
    def explain_gap(self, gap: Dict[str, Any]) -> GapExplanation:
        """Convert a raw gap to executive explanation.
        
        Args:
            gap: Raw gap dict from gap analyzer
            
        Returns:
            GapExplanation with human-readable content
        """
        entity_id = gap.get("entity_id", "Unknown")
        metric_name = gap.get("metric_name", "Unknown Metric")
        plan_value = gap.get("plan_value")
        actual_value = gap.get("actual_value")
        absolute_gap = gap.get("absolute_gap", 0)
        percentage_gap = gap.get("percentage_gap", 0)
        direction = gap.get("direction", "under")
        severity = gap.get("severity", "normal")
        
        # Translate metric name
        translated_metric = self.vocab.translate_metric(metric_name)
        translated_direction = self.vocab.translate_direction(direction)
        
        # Generate headline
        headline = self._generate_gap_headline(
            translated_metric, translated_direction, percentage_gap, severity
        )
        
        # Generate summary
        summary = self._generate_gap_summary(
            entity_id, translated_metric, plan_value, actual_value,
            absolute_gap, percentage_gap, direction
        )
        
        # Generate business impact
        business_impact = self._generate_gap_impact(
            translated_metric, absolute_gap, percentage_gap, severity
        )
        
        # Generate root cause hypothesis
        root_cause = self._generate_gap_root_cause(direction, percentage_gap)
        
        # Generate recommended action
        recommended_action = self._generate_gap_action(direction, severity)
        
        # Generate metric context
        metric_context = self._generate_metric_context(translated_metric, plan_value, actual_value)
        
        return GapExplanation(
            headline=headline,
            summary=summary,
            business_impact=business_impact,
            root_cause=root_cause,
            recommended_action=recommended_action,
            metric_context=metric_context,
            severity=severity,
            plan_value=plan_value,
            actual_value=actual_value,
            variance_value=absolute_gap,
            variance_percent=percentage_gap
        )
    
    def explain_entity(self, entity: Dict[str, Any]) -> EntityExplanation:
        """Convert a raw entity to executive explanation."""
        name = entity.get("canonical_name", "Unknown")
        cardinality = entity.get("cardinality", 0)
        source_sheets = entity.get("source_sheets", [])
        is_primary = entity.get("is_primary", False)
        related_count = entity.get("related_count", 0)
        
        # Translate entity name
        translated_name = self.vocab.translate_entity(name)
        
        # Generate description
        description = self._generate_entity_description(translated_name, cardinality, is_primary)
        
        # Generate significance
        significance = self._generate_entity_significance(
            translated_name, cardinality, len(source_sheets), is_primary
        )
        
        # Generate data coverage
        data_coverage = self._generate_data_coverage(source_sheets)
        
        # Generate relationship summary
        relationship_summary = self._generate_relationship_summary(related_count)
        
        return EntityExplanation(
            name=translated_name,
            description=description,
            significance=significance,
            data_coverage=data_coverage,
            cardinality=cardinality,
            relationship_summary=relationship_summary
        )
    
    def explain_constraint(self, constraint: Dict[str, Any]) -> Dict[str, str]:
        """Convert a raw constraint to executive explanation."""
        constraint_type = constraint.get("constraint_type", "unknown")
        description = constraint.get("description", "")
        severity = constraint.get("severity", "medium")
        entity_id = constraint.get("entity_id")
        
        translated_type = self.vocab.translate_constraint_type(constraint_type)
        
        return {
            "type": translated_type,
            "headline": f"{translated_type} Identified",
            "summary": self._clean_constraint_description(description),
            "impact": self._generate_constraint_impact(constraint_type, severity),
            "recommendation": self._generate_constraint_recommendation(constraint_type),
            "affected_entity": entity_id,
            "severity": severity
        }
    
    # =========================================
    # DECISION GENERATION HELPERS
    # =========================================
    
    def _generate_decision_headline(
        self, 
        decision_type: str, 
        summary: str, 
        impact_score: float
    ) -> str:
        """Generate executive headline for decision."""
        translated_type = self.vocab.translate_decision_type(decision_type)
        
        impact_qualifier = ""
        if impact_score >= 0.8:
            impact_qualifier = "High-Impact "
        elif impact_score >= 0.5:
            impact_qualifier = "Material "
        
        # Extract key numbers from summary if present
        if "critical gaps" in summary.lower():
            import re
            match = re.search(r'(\d+)\s+critical', summary.lower())
            if match:
                count = match.group(1)
                return f"{impact_qualifier}{translated_type}: {count} Material Variances Detected"
        
        return f"{impact_qualifier}{translated_type}"
    
    def _generate_decision_summary(
        self,
        decision_type: str,
        raw_summary: str,
        gap_count: int,
        constraint_count: int
    ) -> str:
        """Generate plain English summary."""
        context = self.vocab.get_industry_context()
        
        if "underperformance" in raw_summary.lower():
            return (
                f"Analysis indicates {context['performance_unit']} is tracking below "
                f"{context['target_unit']} across {gap_count} measurement points. "
                f"This pattern suggests systematic underdelivery requiring attention."
            )
        elif "overperformance" in raw_summary.lower():
            return (
                f"Results are exceeding {context['target_unit']}s across {gap_count} metrics. "
                f"While positive, this may indicate conservative target-setting that warrants review."
            )
        elif "constraint" in raw_summary.lower() or "dependency" in raw_summary.lower():
            return (
                f"Execution is impacted by {constraint_count} identified constraint(s). "
                f"Resolution is required to unlock downstream progress."
            )
        elif "systemic" in raw_summary.lower():
            return (
                f"A systemic pattern has been identified affecting multiple {context['entity_unit']}s. "
                f"This requires strategic intervention rather than tactical fixes."
            )
        else:
            return (
                f"Analysis has identified findings requiring review. "
                f"{gap_count} variance(s) and {constraint_count} constraint(s) were detected."
            )
    
    def _generate_business_impact(
        self,
        decision_type: str,
        impact_score: float,
        gap_count: int
    ) -> str:
        """Generate business impact statement."""
        impact_percent = int(impact_score * 100)
        
        if impact_score >= 0.8:
            return (
                f"High business impact ({impact_percent}% severity score). "
                f"Affects {gap_count} performance indicators. "
                f"Immediate attention recommended to prevent further deviation."
            )
        elif impact_score >= 0.5:
            return (
                f"Moderate business impact ({impact_percent}% severity score). "
                f"Could affect quarterly objectives if left unaddressed."
            )
        else:
            return (
                f"Lower business impact ({impact_percent}% severity score). "
                f"Should be monitored but may not require immediate intervention."
            )
    
    def _generate_root_cause(self, decision_type: str, reasoning: str) -> str:
        """Generate root cause explanation."""
        # Clean up the technical reasoning
        if not reasoning:
            return "Root cause analysis pending. Additional data may be required."
        
        # Extract key insights from reasoning
        if "deviation from targets" in reasoning.lower():
            return (
                "Primary driver appears to be systematic variance from established targets. "
                "This could stem from target-setting methodology, execution gaps, or market conditions."
            )
        elif "constraints" in reasoning.lower():
            return (
                "Identified constraints are limiting execution capability. "
                "Root cause likely involves upstream dependencies or resource limitations."
            )
        else:
            # Clean up and return
            cleaned = reasoning.split(". ")[0] + "."
            return cleaned if len(cleaned) > 20 else reasoning[:200]
    
    def _generate_recommended_action(
        self,
        decision_type: str,
        urgency_score: float
    ) -> str:
        """Generate recommended action."""
        actions = {
            "investigate": "Conduct detailed analysis to identify specific drivers and develop targeted remediation plan.",
            "investigate_systemic": "Initiate cross-functional review to identify systemic issues and develop comprehensive resolution strategy.",
            "escalate": "Escalate to leadership with impact assessment and proposed intervention options.",
            "monitor": "Add to active monitoring list with weekly review cadence. No immediate action required.",
            "resolve": "Develop and execute resolution plan. Assign clear ownership and timeline.",
            "prioritize": "Prioritize resources toward this issue. May require reallocation from lower-impact activities.",
            "allocate": "Review resource allocation and rebalance as needed to address identified gaps.",
            "sequence": "Develop sequencing plan to address dependencies in correct order.",
            "verify_targets": "Review target-setting methodology and recalibrate if warranted by market conditions."
        }
        
        base_action = actions.get(decision_type, "Review findings and determine appropriate response.")
        
        if urgency_score >= 0.8:
            return f"URGENT: {base_action} Timeline: Immediate action within 24-48 hours."
        elif urgency_score >= 0.6:
            return f"{base_action} Timeline: Address within current review cycle."
        else:
            return f"{base_action} Timeline: Include in next planning cycle."
    
    def _generate_confidence_rationale(
        self,
        confidence_score: float,
        gap_count: int,
        constraint_count: int
    ) -> str:
        """Generate confidence rationale."""
        confidence_percent = int(confidence_score * 100)
        
        data_points = gap_count + constraint_count
        
        if confidence_score >= 0.8:
            return (
                f"High confidence ({confidence_percent}%) based on {data_points} supporting data points. "
                f"Pattern is statistically significant and consistent across multiple dimensions."
            )
        elif confidence_score >= 0.6:
            return (
                f"Moderate confidence ({confidence_percent}%) based on {data_points} data points. "
                f"Finding is directionally clear but additional validation may strengthen the conclusion."
            )
        else:
            return (
                f"Lower confidence ({confidence_percent}%). "
                f"Limited data points available. Recommend gathering additional evidence before acting."
            )
    
    # =========================================
    # GAP GENERATION HELPERS
    # =========================================
    
    def _generate_gap_headline(
        self,
        metric: str,
        direction: str,
        percentage: float,
        severity: str
    ) -> str:
        """Generate gap headline."""
        abs_pct = abs(percentage) if percentage else 0
        
        severity_prefix = ""
        if severity == "critical":
            severity_prefix = "Critical: "
        elif severity == "warning":
            severity_prefix = "Warning: "
        
        return f"{severity_prefix}{metric} {direction} by {abs_pct:.1f}%"
    
    def _generate_gap_summary(
        self,
        entity_id: str,
        metric: str,
        plan: float,
        actual: float,
        absolute: float,
        percentage: float,
        direction: str
    ) -> str:
        """Generate gap summary."""
        context = self.vocab.get_industry_context()
        
        plan_str = f"{plan:,.0f}" if plan else "N/A"
        actual_str = f"{actual:,.0f}" if actual else "N/A"
        
        if direction == "under":
            return (
                f"{metric} is {abs(percentage or 0):.1f}% below {context['target_unit']}. "
                f"{context['target_unit'].title()}: {plan_str}. Actual: {actual_str}. "
                f"This represents a {context['variance_term']} of {abs(absolute or 0):,.0f} units."
            )
        elif direction == "over":
            return (
                f"{metric} is {abs(percentage or 0):.1f}% above {context['target_unit']}. "
                f"{context['target_unit'].title()}: {plan_str}. Actual: {actual_str}. "
                f"This represents an excess of {abs(absolute or 0):,.0f} units."
            )
        else:
            return f"{metric} is tracking at {context['target_unit']}. No significant variance detected."
    
    def _generate_gap_impact(
        self,
        metric: str,
        absolute: float,
        percentage: float,
        severity: str
    ) -> str:
        """Generate gap business impact."""
        if severity == "critical":
            return (
                f"Material impact on {metric}. "
                f"Variance of {abs(absolute or 0):,.0f} ({abs(percentage or 0):.1f}%) "
                f"requires immediate attention to prevent cascading effects."
            )
        elif severity == "warning":
            return (
                f"Moderate impact on {metric}. "
                f"Variance is notable and should be addressed to prevent escalation."
            )
        else:
            return f"Minor impact. Within acceptable tolerance but should be monitored."
    
    def _generate_gap_root_cause(self, direction: str, percentage: float) -> str:
        """Generate gap root cause hypothesis."""
        abs_pct = abs(percentage) if percentage else 0
        
        if direction == "under" and abs_pct > 30:
            return (
                "Significant underperformance may indicate fundamental execution issues, "
                "market changes, or overly aggressive target-setting."
            )
        elif direction == "under":
            return (
                "Moderate shortfall could stem from timing differences, "
                "execution variability, or localized challenges."
            )
        elif direction == "over" and abs_pct > 30:
            return (
                "Significant overperformance may indicate conservative targets, "
                "one-time events, or unreported market shifts."
            )
        else:
            return "Within normal operational variance. No specific root cause identified."
    
    def _generate_gap_action(self, direction: str, severity: str) -> str:
        """Generate gap recommended action."""
        if severity == "critical":
            if direction == "under":
                return "Conduct immediate root cause analysis. Develop recovery plan with clear milestones."
            else:
                return "Validate data accuracy. Review target methodology for potential recalibration."
        elif severity == "warning":
            return "Add to monitoring dashboard. Review in next planning cycle."
        else:
            return "Continue standard monitoring. No specific action required."
    
    def _generate_metric_context(
        self,
        metric: str,
        plan: float,
        actual: float
    ) -> str:
        """Generate metric context."""
        context = self.vocab.get_industry_context()
        
        if plan and actual:
            achievement = (actual / plan * 100) if plan != 0 else 0
            return f"{metric} {context['performance_unit']} at {achievement:.1f}% of {context['target_unit']}"
        return f"{metric} performance data"
    
    # =========================================
    # ENTITY GENERATION HELPERS
    # =========================================
    
    def _generate_entity_description(
        self,
        name: str,
        cardinality: int,
        is_primary: bool
    ) -> str:
        """Generate entity description."""
        context = self.vocab.get_industry_context()
        
        if is_primary:
            return (
                f"{name} is a primary dimension with {cardinality:,} unique values. "
                f"This is a core tracking entity across the dataset."
            )
        else:
            return (
                f"{name} represents a categorical dimension with {cardinality:,} unique values."
            )
    
    def _generate_entity_significance(
        self,
        name: str,
        cardinality: int,
        sheet_count: int,
        is_primary: bool
    ) -> str:
        """Generate entity significance."""
        if is_primary and sheet_count > 1:
            return (
                f"High significance. {name} appears across {sheet_count} data sources "
                f"and serves as a key linkage dimension for analysis."
            )
        elif cardinality > 100:
            return f"Moderate significance. Large dimension with {cardinality:,} distinct values."
        else:
            return "Standard dimension used for data categorization."
    
    def _generate_data_coverage(self, source_sheets: List[str]) -> str:
        """Generate data coverage description."""
        if len(source_sheets) > 2:
            return f"Present in {len(source_sheets)} data sources: {', '.join(source_sheets[:3])}{'...' if len(source_sheets) > 3 else ''}"
        elif source_sheets:
            return f"Present in: {', '.join(source_sheets)}"
        else:
            return "Data coverage information unavailable"
    
    def _generate_relationship_summary(self, related_count: int) -> str:
        """Generate relationship summary."""
        if related_count > 5:
            return f"Highly connected with {related_count} related entities"
        elif related_count > 0:
            return f"Connected to {related_count} other dimension(s)"
        else:
            return "Standalone dimension with no detected relationships"
    
    # =========================================
    # CONSTRAINT HELPERS
    # =========================================
    
    def _clean_constraint_description(self, description: str) -> str:
        """Clean up constraint description for executive consumption."""
        # Remove technical prefixes
        cleaned = description.replace("Status indicates ", "")
        cleaned = cleaned.replace("Extracted from remark: ", "")
        cleaned = cleaned.replace("Rare category value: ", "Anomaly detected: ")
        return cleaned[:200] if len(cleaned) > 200 else cleaned
    
    def _generate_constraint_impact(self, constraint_type: str, severity: str) -> str:
        """Generate constraint impact statement."""
        impacts = {
            "blocking": "Prevents downstream execution until resolved",
            "deadline": "Time-sensitive constraint requiring prioritization",
            "dependency": "Upstream dependency must be addressed first",
            "capacity": "Resource or capacity limitation affecting throughput",
            "resource": "Resource gap impacting execution capability",
            "exception": "Anomaly requiring investigation"
        }
        
        base_impact = impacts.get(constraint_type, "May impact execution")
        
        if severity == "high":
            return f"Critical: {base_impact}"
        return base_impact
    
    def _generate_constraint_recommendation(self, constraint_type: str) -> str:
        """Generate constraint recommendation."""
        recommendations = {
            "blocking": "Escalate for immediate resolution",
            "deadline": "Review timeline and adjust priorities",
            "dependency": "Engage upstream stakeholders",
            "capacity": "Evaluate resource reallocation options",
            "resource": "Assess staffing or capability gaps",
            "exception": "Investigate anomaly root cause"
        }
        return recommendations.get(constraint_type, "Review and determine appropriate action")
    
    # =========================================
    # UTILITY HELPERS
    # =========================================
    
    def _score_to_severity(self, impact: float, urgency: float) -> str:
        """Convert scores to severity label."""
        combined = (impact + urgency) / 2
        if combined >= 0.7:
            return "critical"
        elif combined >= 0.4:
            return "warning"
        return "normal"
    
    def to_dict(self, explanation: Any) -> Dict[str, Any]:
        """Convert explanation to dictionary."""
        return asdict(explanation)
