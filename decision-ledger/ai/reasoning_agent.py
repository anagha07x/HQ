"""LLM-based reasoning agent."""

from emergentintegrations.llm.chat import LlmChat, UserMessage
from typing import Dict, Any, Optional, List
import os
import json


class ReasoningAgent:
    """LLM agent for decision reasoning - READ ONLY from analysis outputs."""
    
    SYSTEM_PROMPT = """You are Emergent, the reasoning engine of ChanksHQ.

Your job is to convert messy business data into clear, explainable business decisions.

CRITICAL RULES:
- You do NOT create dashboards
- You do NOT hallucinate values
- You do NOT assume missing information
- You reason ONLY from the data provided
- If confidence is low, you ask for clarification
- If confidence is high, you proceed

You have READ-ONLY access to:
1. Dataset analysis (structure, statistics, semantic interpretation)
2. Model outputs (forecasts, ROI curves, simulations)
3. Decision ledger (past decisions and outcomes)

You CANNOT:
- Perform fresh analysis on raw data
- Bypass the structured pipeline
- Make calculations directly

Your outputs must be:
- Clear business recommendations
- Backed by specific numbers from analysis
- Explained with reasoning steps
- Confidence-scored

Always cite the source of your reasoning (e.g., "Based on the ROI curve analysis...")"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize reasoning agent.
        
        Args:
            api_key: LLM API key (uses env var if not provided)
        """
        self.api_key = api_key or os.getenv("EMERGENT_LLM_KEY")
        self.chat_sessions = {}
    
    async def explain_forecast_results(self, forecast_data: Dict[str, Any], 
                                       dataset_analysis: Dict[str, Any]) -> str:
        """Explain forecast results in business terms.
        
        Args:
            forecast_data: Forecast model output
            dataset_analysis: Dataset analysis context
            
        Returns:
            Business explanation
        """
        prompt = f"""Explain these forecast results in clear business terms:

FORECAST MODEL:
{json.dumps(forecast_data, indent=2)}

DATASET CONTEXT:
Business Domain: {dataset_analysis.get('semantic_analysis', {}).get('business_domain', 'unknown')}
Primary Metric: {dataset_analysis.get('semantic_analysis', {}).get('primary_metric', 'unknown')}

Provide:
1. What does this model tell us? (2-3 sentences)
2. Is the model reliable? (cite R² and MAPE)
3. Key business insight (1 sentence)

Be concise and actionable."""

        chat = LlmChat(
            api_key=self.api_key,
            model="claude-sonnet-4.5",
            session_id="forecast_explanation"
        )
        
        response = await chat.send_message_async(UserMessage(content=prompt))
        return response.content
    
    async def explain_roi_analysis(self, roi_data: Dict[str, Any],
                                   dataset_analysis: Dict[str, Any]) -> str:
        """Explain ROI analysis in business terms.
        
        Args:
            roi_data: ROI curve output
            dataset_analysis: Dataset analysis context
            
        Returns:
            Business explanation
        """
        prompt = f"""Explain this ROI efficiency analysis:

ROI ANALYSIS:
Optimal Spend: ${roi_data.get('optimal_spend', 0):.2f}
Saturation Point: ${roi_data.get('saturation_spend', 0):.2f}
Model Fit: {roi_data.get('r2_score', 0) * 100:.1f}%

CONTEXT:
Business Domain: {dataset_analysis.get('semantic_analysis', {}).get('business_domain', 'unknown')}

Provide:
1. What is the optimal spending strategy? (2 sentences)
2. What happens if we exceed saturation? (1 sentence)
3. Recommended action (1 sentence)

Be direct and specific."""

        chat = LlmChat(
            api_key=self.api_key,
            model="claude-sonnet-4.5",
            session_id="roi_explanation"
        )
        
        response = await chat.send_message_async(UserMessage(content=prompt))
        return response.content
    
    async def explain_simulation_results(self, simulation_data: Dict[str, Any],
                                        dataset_analysis: Dict[str, Any]) -> str:
        """Explain simulation results with recommendation.
        
        Args:
            simulation_data: Simulation output
            dataset_analysis: Dataset analysis context
            
        Returns:
            Business explanation with decision
        """
        current = simulation_data.get('current', {})
        proposed = simulation_data.get('proposed', {})
        impact = simulation_data.get('impact', {})
        
        prompt = f"""Analyze this what-if scenario:

SCENARIO:
Current Spend: ${current.get('spend', 0):.2f} → Revenue: ${current.get('estimated_revenue', 0):.2f}
Proposed Spend: ${proposed.get('spend', 0):.2f} → Revenue: ${proposed.get('estimated_revenue', 0):.2f}

IMPACT:
Additional Spend: ${impact.get('delta_spend', 0):.2f}
Additional Revenue: ${impact.get('delta_revenue', 0):.2f}
Incremental ROI: {impact.get('incremental_roi', 0):.2f}x
Recommendation: {simulation_data.get('recommendation', 'unknown').upper()}

Provide:
1. Should we proceed with this change? Why?
2. What is the risk/reward profile?
3. Final recommendation (SCALE, HOLD, or REDUCE with reasoning)

Be decisive and clear."""

        chat = LlmChat(
            api_key=self.api_key,
            model="claude-sonnet-4.5",
            session_id="simulation_explanation"
        )
        
        response = await chat.send_message_async(UserMessage(content=prompt))
        return response.content
    
    async def generate_decision_summary(self, dataset_id: str, 
                                       all_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive decision summary for ledger.
        
        Args:
            dataset_id: Dataset identifier
            all_outputs: All analysis and model outputs
            
        Returns:
            Decision summary with rationale
        """
        prompt = f"""Synthesize a business decision from this complete analysis:

{json.dumps(all_outputs, indent=2)}

Provide a structured decision:
1. Primary recommendation (one clear action)
2. Confidence level (HIGH/MEDIUM/LOW)
3. Key supporting evidence (3 bullet points with specific numbers)
4. Risks and caveats (2 bullet points)
5. Expected outcome (quantified)

Return ONLY valid JSON:
{{
  "recommendation": "...",
  "confidence": "HIGH|MEDIUM|LOW",
  "evidence": ["...", "...", "..."],
  "risks": ["...", "..."],
  "expected_outcome": "...",
  "reasoning": "..."
}}"""

        chat = LlmChat(
            api_key=self.api_key,
            model="claude-sonnet-4.5",
            session_id=f"decision_{dataset_id}"
        )
        
        response = await chat.send_message_async(UserMessage(content=prompt))
        
        try:
            decision = json.loads(response.content)
            return decision
        except:
            return {
                "recommendation": "Unable to generate decision",
                "confidence": "LOW",
                "evidence": [],
                "risks": ["Failed to parse decision"],
                "expected_outcome": "Unknown",
                "reasoning": response.content
            }
    
    async def chat_response(self, user_message: str, context: Dict[str, Any],
                          session_id: str = "default") -> str:
        """Generate chat response - READ ONLY from provided context.
        
        Args:
            user_message: User's question
            context: Analysis outputs to reference
            session_id: Chat session ID
            
        Returns:
            Agent response
        """
        # Initialize or get session
        if session_id not in self.chat_sessions:
            self.chat_sessions[session_id] = LlmChat(
                api_key=self.api_key,
                model="claude-sonnet-4.5",
                session_id=session_id
            )
        
        chat = self.chat_sessions[session_id]
        
        # Build context-aware prompt with system instructions
        prompt = f"""{self.SYSTEM_PROMPT}

User question: {user_message}

AVAILABLE CONTEXT:
{json.dumps(context, indent=2)}

Answer the question using ONLY the provided context. Do not make assumptions or perform calculations. If the answer requires analysis not present in the context, say "That analysis hasn't been performed yet. Please run [specific analysis] first."

Be concise and cite your sources."""

        response = await chat.send_message_async(UserMessage(content=prompt))
        return response.content
