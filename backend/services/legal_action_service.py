import json
from pathlib import Path

from services.ai_service import GEMINI_API_KEY, call_gemini, extract_json_object
from services.cache_service import cache_service

SUPPORTED_WORKFLOWS = {
    "lost_phone": ["lost phone", "lost mobile", "phone stolen", "mobile stolen", "imei", "stolen phone"],
    "consumer_complaint": ["consumer complaint", "defective product", "refund", "seller refused", "bad product", "service complaint"],
    "tenant_dispute": ["tenant dispute", "landlord", "rent", "eviction", "security deposit", "rental dispute"],
    "employment_complaint": ["employment complaint", "salary not paid", "wrongful termination", "employer", "workplace grievance", "unpaid wages"],
}
GUIDANCE_DISCLAIMER = (
    "This platform provides guidance only. All legal actions must be completed by the user on official government portals."
)
DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "legal_actions.json"


def _load_workflows() -> dict:
    with DATA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


LEGAL_ACTIONS = _load_workflows()


def _fallback_issue_type(problem_description: str) -> str:
    lowered = (problem_description or "").strip().lower()
    for issue_type, keywords in SUPPORTED_WORKFLOWS.items():
        if any(keyword in lowered for keyword in keywords):
            return issue_type
    return "unknown"


def _classify_issue_type(problem_description: str) -> str:
    fallback = _fallback_issue_type(problem_description)
    if not GEMINI_API_KEY:
        return fallback

    cache_key = f"legal_action_classify:{cache_service.make_hash(problem_description)}"
    cached = cache_service.get(cache_key)
    if isinstance(cached, str):
        return cached

    prompt = f"""
Classify the user's situation into one of the supported workflow keys.
Return STRICT JSON only with this schema:
{{
  "issue_type": "lost_phone|consumer_complaint|tenant_dispute|employment_complaint|unknown"
}}

Supported keys:
- lost_phone
- consumer_complaint
- tenant_dispute
- employment_complaint
- unknown

User problem:
{problem_description}
"""

    try:
        parsed = extract_json_object(call_gemini(prompt, timeout_seconds=20))
        issue_type = str(parsed.get("issue_type") or fallback).strip().lower()
        if issue_type not in LEGAL_ACTIONS:
            issue_type = fallback
        cache_service.set(cache_key, issue_type, ttl_seconds=1800)
        return issue_type
    except Exception:
        return fallback


def build_legal_action_guide(problem_description: str) -> dict:
    description = (problem_description or "").strip()
    if not description:
        return {
            "issue_type": "unknown",
            "detected_issue": "Unknown Situation",
            "actions": [],
            "portal": "",
            "portal_label": "",
            "required_info": [],
            "notes": [],
            "disclaimer": GUIDANCE_DISCLAIMER,
        }

    cache_key = f"legal_action_guide:{cache_service.make_hash(description)}"
    cached = cache_service.get(cache_key)
    if isinstance(cached, dict):
        return cached

    issue_type = _classify_issue_type(description)
    workflow = LEGAL_ACTIONS.get(issue_type)
    if not workflow:
        result = {
            "issue_type": "unknown",
            "detected_issue": "No guided workflow detected yet",
            "actions": [
                "Collect all relevant documents and dates.",
                "Use the AI case analysis and lawyer matching features to understand the issue better.",
                "Confirm the correct government or court portal before taking action."
            ],
            "portal": "",
            "portal_label": "",
            "required_info": [
                "identity proof",
                "supporting documents",
                "written timeline of events"
            ],
            "notes": [
                "A dedicated guided workflow is not available for this scenario yet.",
                "Use the marketplace to consult a lawyer if the official path is unclear."
            ],
            "disclaimer": GUIDANCE_DISCLAIMER,
        }
        cache_service.set(cache_key, result, ttl_seconds=1800)
        return result

    result = {
        "issue_type": issue_type,
        "detected_issue": workflow.get("detected_issue") or issue_type.replace("_", " ").title(),
        "actions": workflow.get("actions", []),
        "portal": workflow.get("portal", ""),
        "portal_label": workflow.get("portal_label", ""),
        "required_info": workflow.get("required_info", []),
        "notes": workflow.get("notes", []),
        "disclaimer": GUIDANCE_DISCLAIMER,
    }
    cache_service.set(cache_key, result, ttl_seconds=1800)
    return result
