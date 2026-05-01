import json
import re
from datetime import date, datetime
from typing import Any

from services.ai_service import GEMINI_API_KEY, LEGAL_DEFAULT_AREA, call_gemini, extract_json_object
from services.cache_service import cache_service
from services.mlops_service import get_ai_config
from logging_config import get_logger

logger = get_logger(__name__)


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        unique.append(normalized)
    return unique


def _parse_date(value: str) -> date | None:
    text = (value or "").strip()
    if not text:
        return None

    iso_match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if iso_match:
        try:
            return date.fromisoformat(iso_match.group(0))
        except ValueError:
            return None

    dotted_match = re.search(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b", text)
    if dotted_match:
        day_value, month_value, year_value = dotted_match.groups()
        try:
            return date(int(year_value), int(month_value), int(day_value))
        except ValueError:
            return None

    return None


def _deadline_status(deadline_date: date) -> tuple[str, int]:
    days_until = (deadline_date - date.today()).days
    if days_until < 0:
        return "overdue", days_until
    if days_until <= 7:
        return "upcoming", days_until
    return "future", days_until


def _extract_deadlines(case_brief: dict[str, Any], timeline_events: list[dict[str, Any]], analysis: dict[str, Any]) -> list[dict[str, Any]]:
    raw_items: list[tuple[str, str]] = []

    for entry in _as_list(case_brief.get("timeline")):
        raw_items.append((entry, "case_brief"))

    for entry in _as_list(case_brief.get("documents")):
        parsed = _parse_date(entry)
        if parsed is not None:
            raw_items.append((entry, "documents"))

    for entry in _as_list(analysis.get("key_dates")):
        raw_items.append((entry, "document_analysis"))

    for event in timeline_events:
        event_date = str(event.get("event_date") or "").strip()
        description = str(event.get("description") or "Timeline event").strip()
        if event_date:
            raw_items.append((f"{event_date}: {description}", "timeline_event"))

    deadlines: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    for label, source in raw_items:
        parsed_date = _parse_date(label)
        if parsed_date is None:
            continue
        status, days_until = _deadline_status(parsed_date)
        dedupe_key = f"{parsed_date.isoformat()}::{label.lower()}"
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        deadlines.append(
            {
                "title": label,
                "date": parsed_date.isoformat(),
                "status": status,
                "days_until": days_until,
                "source": source,
            }
        )

    deadlines.sort(key=lambda item: item["date"])
    return deadlines[:8]


def _compute_readiness_score(
    analysis: dict[str, Any],
    case_brief: dict[str, Any],
    timeline_events: list[dict[str, Any]],
    deadlines: list[dict[str, Any]],
) -> int:
    score = 30

    legal_area = (analysis.get("legal_area") or case_brief.get("legal_area") or "").strip()
    issue_type = (analysis.get("issue_type") or "").strip()
    location = (analysis.get("location") or "").strip()
    summary = (analysis.get("summary") or case_brief.get("case_summary") or "").strip()
    documents = _as_list(case_brief.get("documents"))
    timeline = _as_list(case_brief.get("timeline"))

    if legal_area and legal_area.lower() != LEGAL_DEFAULT_AREA.lower():
        score += 15
    if issue_type and issue_type.lower() != "general inquiry":
        score += 10
    if location and location.lower() != "unknown":
        score += 10
    if len(summary) >= 40:
        score += 10
    if documents:
        score += 10
    if timeline or timeline_events:
        score += 10
    if deadlines:
        score += 5

    if bool(analysis.get("uncertainty_flag")):
        score -= 5
    if str(analysis.get("urgency") or "").strip().lower() == "high" and not deadlines:
        score -= 10

    return max(0, min(100, score))


def _score_band(score: int) -> str:
    if score >= 80:
        return "Strong"
    if score >= 60:
        return "Good"
    return "Needs Attention"


def _fallback_case_intelligence(
    problem_text: str,
    analysis: dict[str, Any] | None,
    case_brief: dict[str, Any] | None,
    timeline_events: list[dict[str, Any]] | None,
    document_names: list[str] | None,
) -> dict[str, Any]:
    analysis = analysis or {}
    case_brief = case_brief or {}
    timeline_events = timeline_events or []
    document_names = document_names or []

    legal_area = str(analysis.get("legal_area") or case_brief.get("legal_area") or LEGAL_DEFAULT_AREA).strip()
    issue_type = str(analysis.get("issue_type") or "General Inquiry").strip()
    location = str(analysis.get("location") or "Unknown").strip()
    urgency = str(analysis.get("urgency") or "Medium").strip()
    summary = str(analysis.get("summary") or case_brief.get("case_summary") or problem_text).strip()

    case_documents = _dedupe(_as_list(case_brief.get("documents")) + document_names)
    deadlines = _extract_deadlines(case_brief, timeline_events, analysis)
    readiness_score = _compute_readiness_score(analysis, case_brief, timeline_events, deadlines)

    missing_information: list[str] = []
    if not legal_area or legal_area.lower() == LEGAL_DEFAULT_AREA.lower():
        missing_information.append("Clarify the exact legal area or dispute category.")
    if not issue_type or issue_type.lower() == "general inquiry":
        missing_information.append("Describe the specific trigger event or issue type.")
    if not location or location.lower() == "unknown":
        missing_information.append("Add the relevant city, court, landlord, employer, or counterparty location.")
    if not case_documents:
        missing_information.append("Upload contracts, letters, notices, invoices, screenshots, or other supporting documents.")
    if not deadlines:
        missing_information.append("Capture the key dates already known, including notices received, deadlines, and hearing dates.")

    follow_up_questions = _dedupe(
        [
            "What happened first, and on what date did the dispute start?",
            "Which documents or written communications already exist?",
            "Has any authority, landlord, employer, insurer, or seller already contacted you in writing?",
            "What outcome are you trying to achieve in the next 7 to 30 days?",
            f"Which facts matter most for a {legal_area} lawyer to evaluate quickly?" if legal_area else "Which facts matter most for a lawyer to evaluate quickly?",
        ]
    )[:5]

    risk_flags: list[str] = []
    if urgency.lower() == "high":
        risk_flags.append("This matter is marked high urgency, so missing deadlines could materially affect options.")
    if bool(analysis.get("uncertainty_flag")):
        risk_flags.append("The AI analysis reported uncertainty, so the facts should be validated with a qualified lawyer.")
    if not case_documents:
        risk_flags.append("Document support is thin right now, which can slow matching and consultation quality.")
    if not deadlines:
        risk_flags.append("No concrete deadline has been captured yet, which creates avoidable timing risk.")
    if location.lower() == "unknown":
        risk_flags.append("Jurisdiction-specific next steps may change once the relevant location is confirmed.")

    if not risk_flags:
        risk_flags.append("Core intake fields are present, but a lawyer should still verify facts, deadlines, and jurisdiction.")

    consultation_documents = case_documents or [
        "All notices, contracts, invoices, or email threads related to the dispute",
        "A simple chronology of key events and dates",
        "Identity and contact details of the other side",
    ]

    consultation_questions = _dedupe(
        [
            "What immediate deadline or procedural risk should be handled first?",
            "Which facts or documents would most change the legal assessment?",
            "What is the strongest practical next step before any formal filing?",
            "What costs, timelines, and likely decision points should I expect?",
        ]
    )

    return {
        "readiness_score": readiness_score,
        "readiness_band": _score_band(readiness_score),
        "missing_information": _dedupe(missing_information)[:5],
        "follow_up_questions": follow_up_questions,
        "risk_flags": _dedupe(risk_flags)[:5],
        "deadlines": deadlines,
        "consultation_prep": {
            "one_line_goal": summary or "Prepare a lawyer-ready version of the matter.",
            "documents_to_bring": consultation_documents[:6],
            "questions_to_ask": consultation_questions[:5],
        },
        "recommended_next_steps": _dedupe(
            _as_list(case_brief.get("recommended_next_steps"))
            + [
                "Confirm the earliest known deadline and record it in the case timeline.",
                "Gather the strongest supporting documents into one upload set.",
                "Use the consultation prep questions to structure the first lawyer conversation.",
            ]
        )[:5],
    }


def _normalize_ai_case_intelligence(raw: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    consultation = raw.get("consultation_prep") if isinstance(raw.get("consultation_prep"), dict) else {}
    deadlines = raw.get("deadlines") if isinstance(raw.get("deadlines"), list) else []

    normalized_deadlines: list[dict[str, Any]] = []
    for item in deadlines:
        if not isinstance(item, dict):
            continue
        raw_date = str(item.get("date") or "").strip()
        parsed_date = _parse_date(raw_date)
        if parsed_date is None:
            continue
        status, days_until = _deadline_status(parsed_date)
        normalized_deadlines.append(
            {
                "title": str(item.get("title") or item.get("label") or parsed_date.isoformat()).strip(),
                "date": parsed_date.isoformat(),
                "status": status,
                "days_until": days_until,
                "source": str(item.get("source") or "ai").strip() or "ai",
            }
        )

    normalized_deadlines.sort(key=lambda item: item["date"])
    score_value = raw.get("readiness_score", fallback["readiness_score"])
    try:
        readiness_score = max(0, min(100, int(score_value)))
    except Exception:
        logger.exception("Failed to parse readiness_score, using fallback")
        readiness_score = fallback["readiness_score"]

    return {
        "readiness_score": readiness_score,
        "readiness_band": _score_band(readiness_score),
        "missing_information": _dedupe(_as_list(raw.get("missing_information")))[:5] or fallback["missing_information"],
        "follow_up_questions": _dedupe(_as_list(raw.get("follow_up_questions")))[:5] or fallback["follow_up_questions"],
        "risk_flags": _dedupe(_as_list(raw.get("risk_flags")))[:5] or fallback["risk_flags"],
        "deadlines": normalized_deadlines or fallback["deadlines"],
        "consultation_prep": {
            "one_line_goal": str(consultation.get("one_line_goal") or fallback["consultation_prep"]["one_line_goal"]).strip(),
            "documents_to_bring": _dedupe(_as_list(consultation.get("documents_to_bring")))[:6]
            or fallback["consultation_prep"]["documents_to_bring"],
            "questions_to_ask": _dedupe(_as_list(consultation.get("questions_to_ask")))[:5]
            or fallback["consultation_prep"]["questions_to_ask"],
        },
        "recommended_next_steps": _dedupe(_as_list(raw.get("recommended_next_steps")))[:5]
        or fallback["recommended_next_steps"],
    }


def build_case_intelligence(
    problem_text: str,
    analysis: dict[str, Any] | None = None,
    case_brief: dict[str, Any] | None = None,
    timeline_events: list[dict[str, Any]] | None = None,
    document_names: list[str] | None = None,
    actor_key: str = "anonymous",
) -> dict[str, Any]:
    fallback = _fallback_case_intelligence(
        problem_text,
        analysis,
        case_brief,
        timeline_events,
        document_names,
    )

    seed = json.dumps(
        {
            "problem_text": problem_text,
            "analysis": analysis or {},
            "case_brief": case_brief or {},
            "timeline_events": timeline_events or [],
            "document_names": document_names or [],
        },
        sort_keys=True,
        ensure_ascii=True,
    )
    cache_key = f"case_intelligence:{cache_service.make_hash(seed)}"
    cached = cache_service.get(cache_key)
    if cached:
        return cached

    if not problem_text.strip() or not GEMINI_API_KEY:
        cache_service.set(cache_key, fallback, ttl_seconds=1800)
        return fallback

    if not cache_service.allow_request("case_intelligence", actor_key, limit=20, window_seconds=60):
        fallback["rate_limited"] = True
        cache_service.set(cache_key, fallback, ttl_seconds=300)
        return fallback

    prompt = f"""
You are preparing an intake-readiness report for a legal marketplace focused on Germany.
Return STRICT JSON only with this schema:
{{
  "readiness_score": 0,
  "missing_information": ["..."],
  "follow_up_questions": ["..."],
  "risk_flags": ["..."],
  "deadlines": [
    {{"title": "...", "date": "YYYY-MM-DD", "source": "timeline|document|analysis|ai"}}
  ],
  "consultation_prep": {{
    "one_line_goal": "...",
    "documents_to_bring": ["..."],
    "questions_to_ask": ["..."]
  }},
  "recommended_next_steps": ["..."]
}}

Rules:
- Do not invent dates unless they are strongly implied by the provided facts.
- Keep output practical, short, and lawyer-ready.
- If details are missing, use follow-up questions and missing_information instead of guessing.
- Treat the output as informational support, not legal advice.

Problem text:
{problem_text}

Structured analysis:
{json.dumps(analysis or {{}}, ensure_ascii=True)}

Case brief:
{json.dumps(case_brief or {{}}, ensure_ascii=True)}

Timeline events:
{json.dumps(timeline_events or [], ensure_ascii=True)}

Document names:
{json.dumps(document_names or [], ensure_ascii=True)}
"""

    try:
        parsed = extract_json_object(
            call_gemini(
                prompt,
                timeout_seconds=get_ai_config().analysis_timeout_seconds,
                telemetry={
                    "event_name": "case_intelligence_analysis",
                    "input_length": len(problem_text),
                    "timeline_count": len(timeline_events or []),
                    "document_count": len(document_names or []),
                },
            )
        )
        if not isinstance(parsed, dict):
            cache_service.set(cache_key, fallback, ttl_seconds=1800)
            return fallback
        intelligence = _normalize_ai_case_intelligence(parsed, fallback)
        cache_service.set(cache_key, intelligence, ttl_seconds=1800)
        return intelligence
    except Exception:
        logger.exception("case_intelligence generation failed, returning fallback")
        cache_service.set(cache_key, fallback, ttl_seconds=1800)
        return fallback