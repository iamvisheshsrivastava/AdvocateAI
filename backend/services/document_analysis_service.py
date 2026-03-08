import base64
import io
import json
from typing import Any

import pdfplumber
import requests

from services.ai_service import GEMINI_API_KEY, call_gemini, extract_json_object
from services.ai_service import LEGAL_DEFAULT_AREA, build_case_brief
from services.cache_service import cache_service


ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}


def _fallback_analysis() -> dict[str, Any]:
    return {
        "document_type": "Unknown",
        "legal_area": LEGAL_DEFAULT_AREA,
        "key_dates": [],
        "summary": "Unable to analyze document content.",
        "potential_issue": "Unknown",
        "recommended_action": "Consult a qualified lawyer for review.",
        "confidence_level": "Low",
        "citations": [],
    }


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    pages_text: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages_text.append(text.strip())

    combined = "\n\n".join(pages_text)
    return combined[:15000]


def _analysis_prompt_from_text(text: str) -> str:
    return f"""
Analyze the following legal document and return structured information.

Return JSON with the following fields:
- document_type
- legal_area
- key_dates
- summary
- potential_issue
- recommended_action
- confidence_level
- citations

The response must be valid JSON.

Document content:
{text}
"""


def _analysis_prompt_for_image() -> str:
    return """
Analyze this legal document image and return structured information.

Return JSON with the following fields:
- document_type
- legal_area
- key_dates
- summary
- potential_issue
- recommended_action
- confidence_level
- citations

The response must be valid JSON.
"""


def _normalize_analysis(raw: dict[str, Any]) -> dict[str, Any]:
    fallback = _fallback_analysis()

    key_dates = raw.get("key_dates", [])
    if not isinstance(key_dates, list):
        key_dates = [str(key_dates)]

    return {
        "document_type": str(raw.get("document_type") or fallback["document_type"]).strip(),
        "legal_area": str(raw.get("legal_area") or fallback["legal_area"]).strip(),
        "key_dates": [str(item) for item in key_dates],
        "summary": str(raw.get("summary") or fallback["summary"]).strip(),
        "potential_issue": str(raw.get("potential_issue") or fallback["potential_issue"]).strip(),
        "recommended_action": str(
            raw.get("recommended_action") or fallback["recommended_action"]
        ).strip(),
        "confidence_level": str(raw.get("confidence_level") or fallback["confidence_level"]).strip(),
        "citations": [str(item).strip() for item in raw.get("citations", []) if str(item).strip()],
    }


def _analyze_with_text(text: str) -> dict[str, Any]:
    if not text.strip():
        return _fallback_analysis()

    try:
        prompt = _analysis_prompt_from_text(text)
        response_text = call_gemini(prompt, timeout_seconds=35)
        parsed = extract_json_object(response_text)
        if not isinstance(parsed, dict) or not parsed:
            return _fallback_analysis()
        return _normalize_analysis(parsed)
    except Exception:
        return _fallback_analysis()


def _analyze_with_image(file_bytes: bytes, mime_type: str) -> dict[str, Any]:
    try:
        if not GEMINI_API_KEY:
            return _fallback_analysis()

        encoded = base64.b64encode(file_bytes).decode("utf-8")
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": _analysis_prompt_for_image()},
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": encoded,
                            }
                        },
                    ]
                }
            ]
        }
        response = requests.post(url, json=payload, timeout=35)
        response.raise_for_status()
        result = response.json()
        response_text = result["candidates"][0]["content"]["parts"][0]["text"]

        if not response_text.strip():
            return _fallback_analysis()

        parsed = extract_json_object(response_text)
        if not isinstance(parsed, dict) or not parsed:
            return _fallback_analysis()

        return _normalize_analysis(parsed)
    except Exception:
        return _fallback_analysis()


def analyze_document(
    file_name: str,
    content_type: str | None,
    file_bytes: bytes,
    actor_key: str = "anonymous",
) -> dict[str, Any]:
    extension = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported file type. Only PDF, JPG, JPEG, and PNG are allowed.")

    cache_key = f"document_analysis:{cache_service.make_hash(file_name + str(len(file_bytes)) + file_bytes[:256].hex())}"
    cached = cache_service.get(cache_key)
    if cached:
        return cached

    if not cache_service.allow_request("document_analysis", actor_key, limit=20, window_seconds=60):
        fallback = _fallback_analysis()
        fallback["rate_limited"] = True
        fallback["case_brief"] = build_case_brief(
            fallback["summary"],
            analysis={"legal_area": fallback["legal_area"], "summary": fallback["summary"]},
            document_names=[file_name],
            actor_key=actor_key,
        )
        return fallback

    if extension == "pdf":
        extracted_text = _extract_text_from_pdf(file_bytes)
        analysis = _analyze_with_text(extracted_text)
    else:
        mime = content_type or ("image/png" if extension == "png" else "image/jpeg")
        analysis = _analyze_with_image(file_bytes, mime)

    analysis["case_brief"] = build_case_brief(
        analysis.get("summary", ""),
        analysis={
            "legal_area": analysis.get("legal_area"),
            "summary": analysis.get("summary"),
        },
        document_names=[file_name],
        actor_key=actor_key,
    )
    cache_service.set(cache_key, analysis, ttl_seconds=1800)
    return analysis


def analyze_documents(files: list[tuple[str, str | None, bytes]], actor_key: str = "anonymous") -> dict[str, Any]:
    if not files:
        raise ValueError("At least one document is required.")

    analyses = [
        analyze_document(name, content_type, payload, actor_key=actor_key)
        for name, content_type, payload in files
    ]
    combined_text = "\n".join([item.get("summary", "") for item in analyses if item.get("summary")])
    legal_areas = [item.get("legal_area") for item in analyses if item.get("legal_area")]
    primary_legal_area = legal_areas[0] if legal_areas else LEGAL_DEFAULT_AREA
    brief = build_case_brief(
        combined_text,
        analysis={
            "legal_area": primary_legal_area,
            "summary": combined_text,
        },
        document_names=[name for name, _, _ in files],
        actor_key=actor_key,
    )

    return {
        "document_type": "Multi-document packet" if len(analyses) > 1 else analyses[0].get("document_type"),
        "legal_area": primary_legal_area,
        "key_dates": [date for item in analyses for date in item.get("key_dates", [])],
        "summary": combined_text or analyses[0].get("summary", ""),
        "potential_issue": analyses[0].get("potential_issue", "Unknown"),
        "recommended_action": analyses[0].get("recommended_action", ""),
        "confidence_level": analyses[0].get("confidence_level", "Low"),
        "citations": [citation for item in analyses for citation in item.get("citations", [])],
        "case_brief": brief,
        "documents": analyses,
    }
