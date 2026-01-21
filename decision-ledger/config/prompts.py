"""Prompt templates for LLM reasoning."""


class PromptTemplates:
    """Collection of prompt templates for different tasks."""
    
    SYSTEM_PROMPT = """
You are a decision analysis expert. Your role is to:
1. Analyze data patterns and trends
2. Provide clear reasoning for forecasts
3. Help users make informed decisions
4. Track decision outcomes over time

Be concise, analytical, and data-driven.
"""
    
    DATA_ANALYSIS_PROMPT = """
Analyze the following dataset summary:
{summary}

Provide insights on:
1. Key patterns and trends
2. Potential forecasting challenges
3. Recommended modeling approach
"""
    
    DECISION_REASONING_PROMPT = """
Given the forecast:
{forecast_summary}

And the user's question:
{user_question}

Provide clear reasoning and recommendations.
"""
    
    OUTCOME_ANALYSIS_PROMPT = """
Compare the predicted outcome:
{prediction}

With the actual outcome:
{actual}

Analyze:
1. Accuracy of prediction
2. Factors that may have caused deviation
3. Lessons learned for future decisions
"""


prompt_templates = PromptTemplates()
