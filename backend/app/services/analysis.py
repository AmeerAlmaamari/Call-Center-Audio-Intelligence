import logging
import json
import time
import httpx
from typing import Optional
from ..config import get_settings
from ..utils.error_handling import (
    AnalysisError,
    RateLimitError,
    AnalysisValidator,
    retry_with_backoff,
    log_request,
    log_response,
)

logger = logging.getLogger(__name__)
settings = get_settings()

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemini-3-flash-preview"


async def _make_openrouter_request(client: httpx.AsyncClient, headers: dict, payload: dict) -> dict:
    """Make a request to OpenRouter API with rate limit handling."""
    try:
        response = await client.post(OPENROUTER_API_URL, json=payload, headers=headers)
        
        if response.status_code == 429:
            retry_after = response.headers.get("retry-after", 60)
            raise RateLimitError("OpenRouter API rate limit exceeded", retry_after=int(retry_after))
        
        response.raise_for_status()
        return response.json()
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            raise RateLimitError("OpenRouter API rate limit exceeded")
        raise AnalysisError(
            f"OpenRouter API error: {e.response.status_code} - {e.response.text}",
            status_code=e.response.status_code,
            retryable=e.response.status_code in (500, 502, 503, 504)
        )


async def call_llm(prompt: str, system_prompt: str = "", max_retries: int = 3) -> str:
    """Call OpenRouter API with Gemini model and retry logic."""
    if not settings.OPENROUTER_API_KEY:
        raise AnalysisError("OPENROUTER_API_KEY not configured", status_code=500)

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 4096,
    }

    start_time = time.time()
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        data = await retry_with_backoff(
            _make_openrouter_request,
            client, headers, payload,
            max_retries=max_retries,
            base_delay=2.0
        )
        
        duration_ms = (time.time() - start_time) * 1000
        content = data["choices"][0]["message"]["content"]
        
        log_response("call_llm", {"response_length": len(content)}, duration_ms)
        return content


def parse_json_response(response: str, default: dict = None) -> dict:
    """Extract JSON from LLM response with improved parsing."""
    if default is None:
        default = {}
    
    if not response:
        logger.warning("Empty response received from LLM")
        return default
    
    # Try to find JSON in the response
    try:
        # First, try to parse the entire response as JSON
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from markdown code blocks
    if "```json" in response:
        try:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end > start:
                return json.loads(response[start:end].strip())
        except json.JSONDecodeError:
            pass
    
    # Try to extract JSON from generic code blocks
    if "```" in response:
        try:
            start = response.find("```") + 3
            # Skip language identifier if present
            newline = response.find("\n", start)
            if newline != -1:
                start = newline + 1
            end = response.find("```", start)
            if end > start:
                return json.loads(response[start:end].strip())
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON object in the response
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(response[start:end])
    except json.JSONDecodeError:
        pass
    
    logger.warning(f"Failed to parse JSON from LLM response: {response[:200]}...")
    return default


ANALYSIS_SYSTEM_PROMPT = """You are an expert call center analyst specializing in sales performance evaluation. 
Analyze call transcripts and provide structured insights in JSON format.
Be objective, specific, and provide actionable insights.
All scores should be on a 0-100 scale."""


async def analyze_employee_performance(transcript: str) -> dict:
    """Analyze employee/agent performance from transcript."""
    prompt = f"""Analyze this call center transcript for employee performance.

TRANSCRIPT:
{transcript}

Provide a JSON response with:
{{
    "performance_score": <0-100 overall score>,
    "communication_clarity": <0-100 score for clear communication>,
    "responsiveness": <0-100 score for responding to customer needs>,
    "objection_handling_score": <0-100 score for handling objections>,
    "listening_ratio": <0.0-1.0 estimated ratio of listening vs talking>,
    "performance_explanation": "<detailed explanation of scores and areas for improvement>"
}}"""

    response = await call_llm(prompt, ANALYSIS_SYSTEM_PROMPT)
    return parse_json_response(response)


async def analyze_buying_potential(transcript: str) -> dict:
    """Analyze customer buying potential and intent."""
    prompt = f"""Analyze this call transcript for customer buying potential.

TRANSCRIPT:
{transcript}

Provide a JSON response with:
{{
    "interest_level": "<low|medium|high|unknown>",
    "buying_signals_detected": ["<list of specific buying signals found>"],
    "sentiment_progression": [
        {{"phase": "opening", "sentiment": "<positive|neutral|negative>", "notes": "..."}},
        {{"phase": "middle", "sentiment": "...", "notes": "..."}},
        {{"phase": "closing", "sentiment": "...", "notes": "..."}}
    ],
    "conversion_likelihood": <0-100 probability of conversion>
}}"""

    response = await call_llm(prompt, ANALYSIS_SYSTEM_PROMPT)
    return parse_json_response(response)


async def analyze_call_classification(transcript: str) -> dict:
    """Classify call reason and outcome."""
    prompt = f"""Classify this call transcript.

TRANSCRIPT:
{transcript}

Provide a JSON response with:
{{
    "call_reason": "<product_inquiry|pricing_question|complaint_support|followup_renewal|other>",
    "call_reason_confidence": <0-100>,
    "call_outcome": "<successful_sale|interested_not_converted|not_interested|support_complaint|unknown>",
    "call_outcome_confidence": <0-100>
}}"""

    response = await call_llm(prompt, ANALYSIS_SYSTEM_PROMPT)
    return parse_json_response(response)


async def analyze_products(transcript: str, available_products: list[str]) -> dict:
    """Identify products discussed and recommend products."""
    products_str = ", ".join(available_products) if available_products else "Unknown products"
    
    prompt = f"""Analyze products discussed in this call.

AVAILABLE PRODUCTS: {products_str}

TRANSCRIPT:
{transcript}

Provide a JSON response with:
{{
    "products_discussed": [
        {{"name": "<product name>", "context": "<how it was discussed>", "confidence": <0-100>}}
    ],
    "recommended_products": [
        {{"name": "<product name>", "reason": "<why recommended based on customer needs>", "confidence": <0-100>}}
    ]
}}"""

    response = await call_llm(prompt, ANALYSIS_SYSTEM_PROMPT)
    return parse_json_response(response)


async def analyze_sales_intelligence(transcript: str) -> dict:
    """Detect objections and missed opportunities."""
    prompt = f"""Analyze this call for sales intelligence.

TRANSCRIPT:
{transcript}

Provide a JSON response with:
{{
    "objections_detected": [
        {{
            "type": "<price|features|trust|timing|other>",
            "quote": "<relevant customer quote>",
            "agent_response": "<how agent handled it>",
            "handling_score": <0-100>
        }}
    ],
    "missed_opportunities": [
        {{
            "description": "<what opportunity was missed>",
            "customer_signal": "<what the customer said/did>",
            "recommended_action": "<what agent should have done>"
        }}
    ],
    "missed_opportunity_flag": <true if significant opportunities were missed>
}}"""

    response = await call_llm(prompt, ANALYSIS_SYSTEM_PROMPT)
    return parse_json_response(response)


async def generate_action_items(transcript: str, analysis_summary: str) -> list[dict]:
    """Generate actionable recommendations."""
    prompt = f"""Based on this call transcript and analysis, generate action items.

TRANSCRIPT:
{transcript}

ANALYSIS SUMMARY:
{analysis_summary}

Provide a JSON response with:
{{
    "action_items": [
        {{
            "category": "<followup|training|coaching|other>",
            "priority": "<low|medium|high>",
            "description": "<specific actionable recommendation>"
        }}
    ]
}}"""

    response = await call_llm(prompt, ANALYSIS_SYSTEM_PROMPT)
    result = parse_json_response(response)
    return result.get("action_items", [])


async def run_full_analysis(transcript: str, available_products: list[str] = None) -> dict:
    """
    Run complete analysis pipeline on a transcript with validation and edge case handling.
    
    Handles:
    - Empty or very short transcripts
    - Non-sales calls
    - Multiple speakers
    - Low confidence results
    """
    if available_products is None:
        available_products = []

    # Edge case: Empty or very short transcript
    if not transcript or len(transcript.strip()) < 50:
        logger.warning("Transcript is empty or very short, returning minimal analysis")
        return {
            "performance_score": 0,
            "performance_explanation": "Unable to analyze: transcript is empty or too short",
            "call_reason": "unknown",
            "call_reason_confidence": 0,
            "call_outcome": "unknown",
            "call_outcome_confidence": 0,
            "interest_level": "unknown",
            "conversion_likelihood": 0,
            "buying_signals_detected": [],
            "sentiment_progression": [],
            "products_discussed": [],
            "recommended_products": [],
            "objections_detected": [],
            "missed_opportunities": [],
            "missed_opportunity_flag": False,
            "action_items": [],
            "analysis_warnings": ["Transcript too short for meaningful analysis"],
            "overall_confidence": 0,
        }

    # Run all analysis tasks with error handling for each
    analysis_errors = []
    
    try:
        performance = await analyze_employee_performance(transcript)
    except Exception as e:
        logger.error(f"Performance analysis failed: {e}")
        performance = {"performance_score": None, "performance_explanation": f"Analysis failed: {str(e)}"}
        analysis_errors.append("performance_analysis")
    
    try:
        buying = await analyze_buying_potential(transcript)
    except Exception as e:
        logger.error(f"Buying potential analysis failed: {e}")
        buying = {"interest_level": "unknown", "conversion_likelihood": 0, "buying_signals_detected": []}
        analysis_errors.append("buying_analysis")
    
    try:
        classification = await analyze_call_classification(transcript)
    except Exception as e:
        logger.error(f"Call classification failed: {e}")
        classification = {"call_reason": "unknown", "call_outcome": "unknown"}
        analysis_errors.append("classification")
    
    try:
        products = await analyze_products(transcript, available_products)
    except Exception as e:
        logger.error(f"Product analysis failed: {e}")
        products = {"products_discussed": [], "recommended_products": []}
        analysis_errors.append("product_analysis")
    
    try:
        sales_intel = await analyze_sales_intelligence(transcript)
    except Exception as e:
        logger.error(f"Sales intelligence analysis failed: {e}")
        sales_intel = {"objections_detected": [], "missed_opportunities": [], "missed_opportunity_flag": False}
        analysis_errors.append("sales_intelligence")

    analysis_summary = f"""
Performance Score: {performance.get('performance_score', 'N/A')}
Interest Level: {buying.get('interest_level', 'N/A')}
Call Reason: {classification.get('call_reason', 'N/A')}
Call Outcome: {classification.get('call_outcome', 'N/A')}
Missed Opportunities: {len(sales_intel.get('missed_opportunities', []))}
"""

    try:
        action_items = await generate_action_items(transcript, analysis_summary)
    except Exception as e:
        logger.error(f"Action items generation failed: {e}")
        action_items = []
        analysis_errors.append("action_items")

    # Combine all results
    combined_result = {
        **performance,
        **buying,
        **classification,
        **products,
        **sales_intel,
        "action_items": action_items,
    }
    
    # Validate and enhance the analysis
    is_valid, warnings, enhanced = AnalysisValidator.validate_analysis(combined_result)
    
    # Add error tracking
    if analysis_errors:
        enhanced["analysis_errors"] = analysis_errors
        enhanced["analysis_warnings"] = enhanced.get("analysis_warnings", []) + [
            f"Some analysis components failed: {', '.join(analysis_errors)}"
        ]
    
    # Log summary
    logger.info(
        f"Analysis complete - Performance: {enhanced.get('performance_score', 'N/A')}, "
        f"Confidence: {enhanced.get('overall_confidence', 'N/A'):.0f}%, "
        f"Errors: {len(analysis_errors)}, Warnings: {len(enhanced.get('analysis_warnings', []))}"
    )
    
    return enhanced
