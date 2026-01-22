"""Industry Vocabulary Adapter - Translates technical metrics into industry-specific language.

Supports: pharma, retail, saas, generic (default)
Changes ONLY vocabulary and presentation, NOT logic.
"""

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class VocabularyMapping:
    """Mapping for a single term across industries."""
    technical: str
    generic: str
    pharma: str
    retail: str
    saas: str


class IndustryVocabularyAdapter:
    """Adapts technical terminology to industry-specific business language."""
    
    # Core vocabulary mappings - technical term -> industry translations
    VOCABULARY = {
        # Entities
        "customer": VocabularyMapping(
            technical="Customer Entity",
            generic="Customer",
            pharma="Healthcare Provider",
            retail="Account",
            saas="Client Organization"
        ),
        "customer name": VocabularyMapping(
            technical="Customer Name Entity",
            generic="Customer",
            pharma="Healthcare Provider",
            retail="Account",
            saas="Client"
        ),
        "customer name sold to": VocabularyMapping(
            technical="Customer Sold-To Entity",
            generic="Customer",
            pharma="Healthcare Provider",
            retail="Buyer Account",
            saas="Subscriber"
        ),
        "material": VocabularyMapping(
            technical="Material Entity",
            generic="Product",
            pharma="SKU / Formulation",
            retail="Merchandise",
            saas="Product SKU"
        ),
        "material code": VocabularyMapping(
            technical="Material Code",
            generic="Product Code",
            pharma="NDC / SKU Code",
            retail="Item Number",
            saas="Product ID"
        ),
        "product": VocabularyMapping(
            technical="Product Entity",
            generic="Product",
            pharma="Therapy / Drug",
            retail="Merchandise",
            saas="Service Tier"
        ),
        "seg": VocabularyMapping(
            technical="Segment Entity",
            generic="Segment",
            pharma="Therapeutic Area",
            retail="Category",
            saas="Customer Segment"
        ),
        "region": VocabularyMapping(
            technical="Region Entity",
            generic="Region",
            pharma="Territory",
            retail="Market",
            saas="Geo Zone"
        ),
        
        # Metrics
        "qty": VocabularyMapping(
            technical="Quantity Metric",
            generic="Units",
            pharma="Units Dispensed",
            retail="Units Sold",
            saas="Seat Count"
        ),
        "value": VocabularyMapping(
            technical="Value Metric",
            generic="Revenue",
            pharma="Net Sales",
            retail="GMV",
            saas="ARR"
        ),
        "revenue": VocabularyMapping(
            technical="Revenue Metric",
            generic="Revenue",
            pharma="Net Revenue",
            retail="Sales Revenue",
            saas="MRR"
        ),
        "spend": VocabularyMapping(
            technical="Spend Metric",
            generic="Investment",
            pharma="Trade Spend",
            retail="Marketing Spend",
            saas="CAC"
        ),
        "loss": VocabularyMapping(
            technical="Loss Metric",
            generic="Variance",
            pharma="Revenue Leakage",
            retail="Shrinkage",
            saas="Churn Loss"
        ),
        "sales loss": VocabularyMapping(
            technical="Sales Loss",
            generic="Lost Revenue",
            pharma="Unrealized Revenue",
            retail="Lost Sales",
            saas="Churned ARR"
        ),
        "dispatch": VocabularyMapping(
            technical="Dispatch Metric",
            generic="Shipments",
            pharma="Units Shipped",
            retail="Orders Fulfilled",
            saas="Deployments"
        ),
        "target": VocabularyMapping(
            technical="Target Value",
            generic="Target",
            pharma="Quota",
            retail="Plan",
            saas="Goal"
        ),
        "actual": VocabularyMapping(
            technical="Actual Value",
            generic="Actual",
            pharma="Achievement",
            retail="Performance",
            saas="Realized"
        ),
        "gap": VocabularyMapping(
            technical="Gap Value",
            generic="Variance",
            pharma="Attainment Gap",
            retail="Plan Deviation",
            saas="Target Miss"
        ),
        "forecast": VocabularyMapping(
            technical="Forecast",
            generic="Projection",
            pharma="Demand Forecast",
            retail="Sales Forecast",
            saas="Revenue Forecast"
        ),
        
        # Sheet roles
        "master": VocabularyMapping(
            technical="Master Data Sheet",
            generic="Reference Data",
            pharma="Product Master",
            retail="Item Master",
            saas="Configuration"
        ),
        "transactional": VocabularyMapping(
            technical="Transactional Sheet",
            generic="Activity Data",
            pharma="Prescription Data",
            retail="Transaction Log",
            saas="Usage Events"
        ),
        "plan": VocabularyMapping(
            technical="Plan Sheet",
            generic="Targets",
            pharma="Quotas",
            retail="Budget",
            saas="Goals"
        ),
        "actual": VocabularyMapping(
            technical="Actual Sheet",
            generic="Performance",
            pharma="Sales Results",
            retail="Actuals",
            saas="Metrics"
        ),
        "summary": VocabularyMapping(
            technical="Summary Sheet",
            generic="Overview",
            pharma="Executive Summary",
            retail="Dashboard Data",
            saas="KPI Summary"
        ),
        "comparison": VocabularyMapping(
            technical="Comparison Sheet",
            generic="Variance Analysis",
            pharma="Performance Review",
            retail="Plan vs Actual",
            saas="Goal Tracking"
        ),
        
        # Decision types
        "investigate": VocabularyMapping(
            technical="Investigation Required",
            generic="Review Required",
            pharma="Clinical Review",
            retail="Merchandising Review",
            saas="Account Review"
        ),
        "investigate_systemic": VocabularyMapping(
            technical="Systemic Investigation",
            generic="Strategic Review",
            pharma="Portfolio Assessment",
            retail="Category Strategy Review",
            saas="Segment Analysis"
        ),
        "escalate": VocabularyMapping(
            technical="Escalation Required",
            generic="Executive Attention",
            pharma="Leadership Escalation",
            retail="Management Alert",
            saas="Account Escalation"
        ),
        "monitor": VocabularyMapping(
            technical="Monitoring Required",
            generic="Watch List",
            pharma="Under Observation",
            retail="Performance Watch",
            saas="Health Monitor"
        ),
        "resolve": VocabularyMapping(
            technical="Resolution Required",
            generic="Action Required",
            pharma="Intervention Required",
            retail="Corrective Action",
            saas="Remediation Required"
        ),
        "prioritize": VocabularyMapping(
            technical="Prioritization Required",
            generic="Priority Action",
            pharma="Critical Focus",
            retail="High Priority",
            saas="Urgent Attention"
        ),
        "allocate": VocabularyMapping(
            technical="Allocation Required",
            generic="Resource Allocation",
            pharma="Territory Rebalancing",
            retail="Inventory Reallocation",
            saas="Capacity Planning"
        ),
        "sequence": VocabularyMapping(
            technical="Sequencing Required",
            generic="Dependency Resolution",
            pharma="Launch Sequencing",
            retail="Rollout Planning",
            saas="Implementation Sequencing"
        ),
        "verify_targets": VocabularyMapping(
            technical="Target Verification",
            generic="Goal Recalibration",
            pharma="Quota Validation",
            retail="Budget Review",
            saas="Target Assessment"
        ),
        
        # Constraint types
        "blocking": VocabularyMapping(
            technical="Blocking Constraint",
            generic="Critical Blocker",
            pharma="Regulatory Hold",
            retail="Stock Out",
            saas="Integration Blocker"
        ),
        "deadline": VocabularyMapping(
            technical="Deadline Constraint",
            generic="Time Constraint",
            pharma="Compliance Deadline",
            retail="Seasonal Deadline",
            saas="Contract Deadline"
        ),
        "dependency": VocabularyMapping(
            technical="Dependency Constraint",
            generic="Upstream Dependency",
            pharma="Supply Chain Dependency",
            retail="Vendor Dependency",
            saas="Platform Dependency"
        ),
        "capacity": VocabularyMapping(
            technical="Capacity Constraint",
            generic="Capacity Limit",
            pharma="Manufacturing Capacity",
            retail="Warehouse Capacity",
            saas="Infrastructure Limit"
        ),
        "resource": VocabularyMapping(
            technical="Resource Constraint",
            generic="Resource Gap",
            pharma="Field Force Gap",
            retail="Staffing Gap",
            saas="Engineering Capacity"
        ),
        "exception": VocabularyMapping(
            technical="Exception",
            generic="Anomaly",
            pharma="Clinical Exception",
            retail="Transaction Exception",
            saas="Usage Anomaly"
        ),
        
        # Severity
        "critical": VocabularyMapping(
            technical="Critical Severity",
            generic="Critical",
            pharma="High Risk",
            retail="Urgent",
            saas="P0"
        ),
        "warning": VocabularyMapping(
            technical="Warning Severity",
            generic="Warning",
            pharma="Moderate Risk",
            retail="Attention",
            saas="P1"
        ),
        "normal": VocabularyMapping(
            technical="Normal Severity",
            generic="Normal",
            pharma="Low Risk",
            retail="Standard",
            saas="P2"
        ),
        
        # Directions
        "under": VocabularyMapping(
            technical="Under Target",
            generic="Below Target",
            pharma="Under Quota",
            retail="Below Plan",
            saas="Under Goal"
        ),
        "over": VocabularyMapping(
            technical="Over Target",
            generic="Above Target",
            pharma="Over Quota",
            retail="Above Plan",
            saas="Exceeds Goal"
        ),
        "on_target": VocabularyMapping(
            technical="On Target",
            generic="On Track",
            pharma="At Quota",
            retail="On Plan",
            saas="At Goal"
        ),
    }
    
    SUPPORTED_INDUSTRIES = ["generic", "pharma", "retail", "saas"]
    
    def __init__(self, industry: str = "generic"):
        """Initialize with target industry.
        
        Args:
            industry: One of "generic", "pharma", "retail", "saas"
        """
        self.industry = industry.lower() if industry else "generic"
        if self.industry not in self.SUPPORTED_INDUSTRIES:
            self.industry = "generic"
    
    def translate(self, term: str) -> str:
        """Translate a technical term to industry-specific language.
        
        Args:
            term: Technical term to translate
            
        Returns:
            Industry-specific translation
        """
        term_lower = term.lower().strip()
        
        # Direct match
        if term_lower in self.VOCABULARY:
            mapping = self.VOCABULARY[term_lower]
            return getattr(mapping, self.industry, mapping.generic)
        
        # Partial match - check if term contains a known key
        for key, mapping in self.VOCABULARY.items():
            if key in term_lower or term_lower in key:
                translated = getattr(mapping, self.industry, mapping.generic)
                # Preserve case pattern from original
                if term[0].isupper():
                    return translated.title()
                return translated
        
        # No match - return original with title case
        return term.replace("_", " ").title()
    
    def translate_metric(self, metric_name: str) -> str:
        """Translate a metric name."""
        return self.translate(metric_name)
    
    def translate_entity(self, entity_name: str) -> str:
        """Translate an entity name."""
        return self.translate(entity_name)
    
    def translate_decision_type(self, decision_type: str) -> str:
        """Translate a decision type."""
        return self.translate(decision_type)
    
    def translate_constraint_type(self, constraint_type: str) -> str:
        """Translate a constraint type."""
        return self.translate(constraint_type)
    
    def translate_severity(self, severity: str) -> str:
        """Translate a severity level."""
        return self.translate(severity)
    
    def translate_direction(self, direction: str) -> str:
        """Translate a gap direction."""
        return self.translate(direction)
    
    def translate_sheet_role(self, role: str) -> str:
        """Translate a sheet role."""
        return self.translate(role)
    
    def get_industry_context(self) -> Dict[str, str]:
        """Get industry-specific context labels."""
        contexts = {
            "generic": {
                "performance_unit": "performance",
                "target_unit": "target",
                "entity_unit": "item",
                "currency_prefix": "$",
                "variance_term": "variance"
            },
            "pharma": {
                "performance_unit": "attainment",
                "target_unit": "quota",
                "entity_unit": "account",
                "currency_prefix": "$",
                "variance_term": "gap"
            },
            "retail": {
                "performance_unit": "sales",
                "target_unit": "plan",
                "entity_unit": "store",
                "currency_prefix": "$",
                "variance_term": "deviation"
            },
            "saas": {
                "performance_unit": "ARR",
                "target_unit": "goal",
                "entity_unit": "account",
                "currency_prefix": "$",
                "variance_term": "miss"
            }
        }
        return contexts.get(self.industry, contexts["generic"])
