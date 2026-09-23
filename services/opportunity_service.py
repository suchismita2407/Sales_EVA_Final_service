from __future__ import annotations

import json
import re
from typing import Any

from schemas import OpportunityCreate
from services.input_validator import contains_prompt_injection, contains_sensitive_data
from services.scoring import normalize_score


def validate_opportunity_payload(data: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = OpportunityCreate.model_validate(data)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    cleaned = payload.model_dump()
    for label, value in cleaned.items():
        if not isinstance(value, str):
            continue
        if contains_sensitive_data(value):
            raise ValueError(f"Personal/confidential information is not allowed in '{label}'.")
        if contains_prompt_injection(value):
            raise ValueError(f"Your entry in '{label}' contains unsafe instructions.")

    return cleaned


def validate_chat_query(query: str) -> tuple[bool, str | None]:
    user_query = (query or "").strip()
    if not user_query:
        return False, "Please type something."
    if contains_sensitive_data(user_query):
        return False, "<p>Please do not enter personal or confidential information such as phone numbers, email, Aadhaar, PAN etc.</p>"
    if contains_prompt_injection(user_query):
        return False, "<p>Your query contains unsafe instructions. I cannot proceed.</p>"
    return True, None


def collect_retrieved_documents(results: dict[str, Any], label: str) -> list[str]:
    docs: list[str] = []
    documents = results.get("documents") or []
    if not documents:
        return docs

    first_batch = documents[0] if isinstance(documents, list) and documents else []
    for value in first_batch:
        if value:
            docs.append(f"[{label}] {value}")
    return docs


def extract_llm_json(raw_text: str, fallback: dict[str, Any]) -> dict[str, Any]:
    cleaned_text = raw_text.replace("```json", "").replace("```", "").strip()
    try:
        match = re.search(r"\{[\s\S]*\}", cleaned_text)
        if not match:
            raise ValueError("LLM did not return valid JSON")
        parsed = json.loads(match.group(0))
        if not isinstance(parsed, dict):
            raise ValueError("LLM JSON payload was not an object")
        return parsed
    except (json.JSONDecodeError, TypeError, ValueError):
        return fallback


def build_chat_prompt(user_query: str, kb_context: str) -> str:
    if kb_context:
        return f"""
Respond ONLY using HTML format.

<div class="eva-block">
<h3>Summary</h3>
<p>2-3 sentences answer</p>
<h3>Recommended Offerings</h3>
<ul></ul>
<h3>Relevant Case Studies</h3>
<table border="1" cellspacing="0" cellpadding="4"><tr><th>Case</th><th>Benefit</th></tr></table>
<h3>Business Impact</h3>
<ul></ul>
</div>

User Query:
{user_query}

Use ONLY this info:
{kb_context}
"""

    return f"""
You are EVA, enterprise assistant.
No relevant KB found.

Ask user to mention:

User Query:
{user_query}
"""


def is_smalltalk_query(query: str) -> bool:
    smalltalk_keywords = [
        "hi",
        "hello",
        "hey",
        "how are you",
        "good morning",
        "good evening",
        "good afternoon",
        "who are you",
        "what is your name",
    ]
    return any(query.startswith(keyword) for keyword in smalltalk_keywords)


def is_general_question(query: str) -> bool:
    general_questions = [
        "what is ai",
        "what is cloud",
        "define",
        "explain",
        "difference between",
        "compare",
        "what do you think",
    ]
    return any(item in query for item in general_questions)


def build_executive_summary(
    opportunity: dict[str, Any], recommendations: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Create a concise executive summary that helps sales teams prioritize deals."""
    recs = recommendations or []
    scores = []
    for item in recs:
        value = item.get("score") if isinstance(item, dict) else None
        if value is None and isinstance(item, dict):
            value = item.get("fit_score")
        if value is not None:
            scores.append(float(value))

    fit_score = 0.0
    if scores:
        fit_score = round(sum(normalize_score(score) for score in scores) / len(scores) * 100, 1)

    stage = (opportunity or {}).get("stage", "Discovery")
    stage_weight = {
        "Discovery": 0.55,
        "Qualifying": 0.7,
        "Proposal": 0.82,
        "Negotiation": 0.9,
        "Closed": 1.0,
    }.get(stage, 0.6)
    readiness_score = round(max(0, min(100, fit_score * 0.7 + stage_weight * 30)))

    deal_value = (opportunity or {}).get("value") or "value not set"
    headline = (
        f"{(opportunity or {}).get('name', 'Opportunity')} shows {fit_score}% solution fit "
        f"for a {stage.lower()} deal worth {deal_value}."
    )

    if readiness_score >= 80:
        next_action = "Advance to executive review and finalize a tailored proposal pack."
    elif readiness_score >= 60:
        next_action = "Validate the top offering fit and prepare a stronger customer narrative."
    else:
        next_action = "Strengthen discovery inputs and refine scope before a formal proposal push."

    return {
        "headline": headline,
        "fit_score": int(fit_score),
        "readiness_score": int(readiness_score),
        "next_action": next_action,
        "opportunity_stage": stage,
        "deal_value": deal_value,
        "recommended_offerings": len(recs),
    }
