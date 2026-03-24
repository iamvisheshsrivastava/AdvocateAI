import json
import os
import time
import requests
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

from services.cache_service import cache_service
from services.mlops_service import get_ai_config, log_ai_event

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LEGAL_DEFAULT_AREA = "General Legal"
embed_model = SentenceTransformer("all-MiniLM-L6-v2")
AI_CONFIG = get_ai_config()


def extract_json_object(text: str) -> dict:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(cleaned)
    except Exception:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except Exception:
            return {}

    return {}


def call_gemini(
    prompt: str,
    timeout_seconds: int | None = None,
    *,
    telemetry: dict[str, object] | None = None,
) -> str:
    telemetry = telemetry or {}
    started_at = time.perf_counter()
    resolved_timeout = timeout_seconds or AI_CONFIG.default_timeout_seconds
    event_name = str(telemetry.get("event_name") or "gemini_call")
    actor_key = str(telemetry.get("actor_key") or "anonymous")
    model_name = str(telemetry.get("model_name") or AI_CONFIG.gemini_model)
    cache_hit = bool(telemetry.get("cache_hit", False))

    if not GEMINI_API_KEY:
        log_ai_event(
            event_name,
            started_at=started_at,
            status="skipped",
            input_text=prompt,
            output_text="",
            actor_key=actor_key,
            model_name=model_name,
            cache_hit=cache_hit,
            metadata={**telemetry, "reason": "missing_gemini_api_key"},
        )
        return ""

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_name}:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, json=payload, timeout=resolved_timeout)
        response.raise_for_status()
        result = response.json()
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        log_ai_event(
            event_name,
            started_at=started_at,
            status="success",
            input_text=prompt,
            output_text=text,
            actor_key=actor_key,
            model_name=model_name,
            cache_hit=cache_hit,
            metadata=telemetry,
        )
        return text
    except Exception as exc:
        log_ai_event(
            event_name,
            started_at=started_at,
            status="error",
            input_text=prompt,
            output_text="",
            actor_key=actor_key,
            model_name=model_name,
            cache_hit=cache_hit,
            metadata=telemetry,
            error=exc,
        )
        raise


def _normalize_confidence_level(value: str | None) -> str:
    normalized = (value or "medium").strip().lower()
    if normalized in ("low", "medium", "high"):
        return normalized.capitalize()
    return "Medium"


def _fallback_analysis_result(text: str) -> dict:
    return {
        "is_legal_issue": False,
        "legal_area": LEGAL_DEFAULT_AREA,
        "issue_type": "General Inquiry",
        "location": "Unknown",
        "urgency": "Medium",
        "summary": text.strip(),
        "confidence_level": "Medium",
        "reasoning": "Automated legal analysis is unavailable. Review the facts manually.",
        "recommended_action": "Consult a qualified lawyer in Germany for tailored advice.",
        "citations": [],
        "uncertainty_flag": True,
        "jurisdiction": "Germany",
        "disclaimer": "AdvocateAI provides informational support and is not a substitute for legal advice.",
    }


def _with_case_brief(text: str, payload: dict, actor_key: str) -> dict:
    payload["case_brief"] = build_case_brief(text, payload, actor_key=actor_key)
    return payload


def _parsed_analysis_result(parsed: dict, fallback: dict) -> dict:
    urgency = str(parsed.get("urgency") or "Medium").strip().capitalize()
    if urgency not in ("Low", "Medium", "High"):
        urgency = "Medium"

    return {
        "is_legal_issue": bool(parsed.get("is_legal_issue", True)),
        "legal_area": str(parsed.get("legal_area") or fallback["legal_area"]).strip(),
        "issue_type": str(parsed.get("issue_type") or fallback["issue_type"]).strip(),
        "location": str(parsed.get("location") or fallback["location"]).strip(),
        "urgency": urgency,
        "summary": str(parsed.get("summary") or fallback["summary"]).strip(),
        "confidence_level": _normalize_confidence_level(parsed.get("confidence_level")),
        "reasoning": str(parsed.get("reasoning") or fallback["reasoning"]).strip(),
        "recommended_action": str(
            parsed.get("recommended_action") or fallback["recommended_action"]
        ).strip(),
        "citations": [str(item).strip() for item in parsed.get("citations", []) if str(item).strip()],
        "uncertainty_flag": bool(parsed.get("uncertainty_flag", False)),
        "jurisdiction": str(parsed.get("jurisdiction") or "Germany").strip() or "Germany",
        "disclaimer": fallback["disclaimer"],
    }


def _normalize_case_brief(raw: dict, fallback_text: str, legal_area: str) -> dict:
    def _as_list(value) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    return {
        "case_summary": str(raw.get("case_summary") or fallback_text).strip(),
        "legal_area": str(raw.get("legal_area") or legal_area or LEGAL_DEFAULT_AREA).strip(),
        "key_entities": _as_list(raw.get("key_entities")),
        "timeline": _as_list(raw.get("timeline")),
        "documents": _as_list(raw.get("documents")),
        "recommended_next_steps": _as_list(raw.get("recommended_next_steps")),
    }


def build_case_brief(
    problem_text: str,
    analysis: dict | None = None,
    document_names: list[str] | None = None,
    actor_key: str = "anonymous",
):
    summary_seed = (analysis or {}).get("summary") or problem_text.strip()
    legal_area = (analysis or {}).get("legal_area") or LEGAL_DEFAULT_AREA
    fallback = _normalize_case_brief(
        {
            "case_summary": summary_seed,
            "legal_area": legal_area,
            "key_entities": [],
            "timeline": [],
            "documents": document_names or [],
            "recommended_next_steps": [
                "Collect relevant contracts, notices, and correspondence.",
                "Record important dates and deadlines.",
                "Consult a qualified lawyer in Germany for tailored advice.",
            ],
        },
        fallback_text=summary_seed,
        legal_area=legal_area,
    )

    if not problem_text.strip() or not GEMINI_API_KEY:
        return fallback

    cache_key = f"ai_brief:{cache_service.make_hash(problem_text + json.dumps(document_names or []))}"
    cached = cache_service.get(cache_key)
    if cached:
        return cached

    if not cache_service.allow_request("ai_brief", actor_key, limit=20, window_seconds=60):
        return fallback

    prompt = f"""
You are preparing a structured case brief for a German legal marketplace.
Return STRICT JSON only with this schema:
{{
  "case_summary": "...",
  "legal_area": "...",
  "key_entities": ["..."],
  "timeline": ["..."] ,
  "documents": ["..."],
  "recommended_next_steps": ["..."]
}}

Rules:
- Assume Germany as the primary jurisdiction unless the facts clearly suggest otherwise.
- Keep the summary concise and factual.
- Use empty arrays when unknown.
- Include practical next steps, not guarantees.

Problem details:
{problem_text}

Known analysis:
{json.dumps(analysis or {}, ensure_ascii=True)}

Document names:
{json.dumps(document_names or [], ensure_ascii=True)}
"""

    try:
        parsed = extract_json_object(
            call_gemini(
                prompt,
                timeout_seconds=AI_CONFIG.brief_timeout_seconds,
                telemetry={
                    "event_name": "case_brief_generation",
                    "actor_key": actor_key,
                    "legal_area": legal_area,
                    "document_count": len(document_names or []),
                },
            )
        )
        if not isinstance(parsed, dict):
            return fallback
        brief = _normalize_case_brief(parsed, fallback_text=summary_seed, legal_area=legal_area)
        cache_service.set(cache_key, brief, ttl_seconds=1800)
        return brief
    except Exception:
        return fallback


def analyze_legal_problem(text: str, actor_key: str = "anonymous"):
    fallback = _fallback_analysis_result(text)

    if not text.strip() or not GEMINI_API_KEY:
        return _with_case_brief(text, fallback, actor_key)

    cache_key = f"ai_analysis:{cache_service.make_hash(text)}"
    cached = cache_service.get(cache_key)
    if cached:
        return cached

    if not cache_service.allow_request("ai_analysis", actor_key, limit=30, window_seconds=60):
        fallback["rate_limited"] = True
        return _with_case_brief(text, fallback, actor_key)

    prompt = f"""
You are a legal issue analyzer for a German legal marketplace.
Given the user's message, detect legal domain and return STRICT JSON only.
Use this schema exactly:
{{
  "is_legal_issue": true,
  "legal_area": "...",
  "issue_type": "...",
  "location": "...",
  "urgency": "Low|Medium|High",
  "summary": "...",
  "confidence_level": "Low|Medium|High",
  "reasoning": "...",
  "recommended_action": "...",
  "citations": ["..."],
  "uncertainty_flag": true,
  "jurisdiction": "Germany"
}}

Rules:
- If it is not a legal issue, set is_legal_issue=false and still provide best-effort fields.
- Keep summary concise and practical.
- Default to Germany unless the facts clearly indicate another jurisdiction.
- If you are uncertain, set uncertainty_flag=true and say so in reasoning.
- Include citations only when you can cite broadly recognized legal sources or concepts; otherwise return an empty list.

User message:
{text}
"""

    try:
        text_output = call_gemini(
            prompt,
            timeout_seconds=AI_CONFIG.analysis_timeout_seconds,
            telemetry={
                "event_name": "legal_problem_analysis",
                "actor_key": actor_key,
                "input_length": len(text),
            },
        )
        parsed = extract_json_object(text_output)
        if not isinstance(parsed, dict):
            return _with_case_brief(text, fallback, actor_key)

        result = _parsed_analysis_result(parsed, fallback)
        result = _with_case_brief(text, result, actor_key)
        cache_service.set(cache_key, result, ttl_seconds=900)
        return result
    except Exception:
        return _with_case_brief(text, fallback, actor_key)


def generate_chat_response(user_message: str, context: str = "", actor_key: str = "anonymous") -> str:
    if not GEMINI_API_KEY:
        return "AI response is unavailable."

    cache_key = f"chat_response:{cache_service.make_hash(user_message + context)}"
    cached = cache_service.get(cache_key)
    if cached:
        return str(cached)

    if not cache_service.allow_request("chat_response", actor_key, limit=30, window_seconds=60):
        return "You have reached the temporary AI request limit. Please wait a moment and try again."

    final_prompt = user_message if not context else f"""
User question: {user_message}

Use the following professionals to answer:
{context}

Rules:
- Treat Germany as the default jurisdiction unless stated otherwise.
- Avoid presenting the answer as legal advice.
- Be explicit when facts are missing or uncertain.
- When possible, point to the type of authority or document the user should verify.

Respond naturally and recommend the best options.
"""

    try:
        response = call_gemini(
            final_prompt,
            timeout_seconds=AI_CONFIG.chat_timeout_seconds,
            telemetry={
                "event_name": "chat_response",
                "actor_key": actor_key,
                "context_length": len(context),
                "message_length": len(user_message),
            },
        )
        cache_service.set(cache_key, response, ttl_seconds=900)
        return response
    except Exception:
        return "Sorry, I couldn’t generate a response."
