import base64
import io
from typing import Any

import pdfplumber
import requests

from services.ai_service import GEMINI_API_KEY, call_gemini, extract_json_object


ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}


def _fallback_analysis() -> dict[str, Any]:
    return {
        "document_type": "Unknown",
        "legal_area": "General Legal",
        "key_dates": [],
        "summary": "Unable to analyze document content.",
        "potential_issue": "Unknown",
        "recommended_action": "Consult a qualified lawyer for review.",
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


def analyze_document(file_name: str, content_type: str | None, file_bytes: bytes) -> dict[str, Any]:
    extension = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported file type. Only PDF, JPG, JPEG, and PNG are allowed.")

    if extension == "pdf":
        extracted_text = _extract_text_from_pdf(file_bytes)
        return _analyze_with_text(extracted_text)

    mime = content_type or ("image/png" if extension == "png" else "image/jpeg")
    return _analyze_with_image(file_bytes, mime)
