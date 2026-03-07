import json
import os
import requests
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LEGAL_DEFAULT_AREA = "General Legal"
embed_model = SentenceTransformer("all-MiniLM-L6-v2")


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


def call_gemini(prompt: str, timeout_seconds: int = 20) -> str:
    if not GEMINI_API_KEY:
        return ""

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(url, json=payload, timeout=timeout_seconds)
    response.raise_for_status()
    result = response.json()
    return result["candidates"][0]["content"]["parts"][0]["text"]


def analyze_legal_problem(text: str):
    fallback = {
        "is_legal_issue": False,
        "legal_area": LEGAL_DEFAULT_AREA,
        "issue_type": "General Inquiry",
        "location": "Unknown",
        "urgency": "Medium",
        "summary": text.strip(),
    }

    if not text.strip() or not GEMINI_API_KEY:
        return fallback

    prompt = f"""
You are a legal issue analyzer.
Given the user's message, detect legal domain and return STRICT JSON only.
Use this schema exactly:
{{
  "is_legal_issue": true,
  "legal_area": "...",
  "issue_type": "...",
  "location": "...",
  "urgency": "Low|Medium|High",
  "summary": "..."
}}

Rules:
- If it is not a legal issue, set is_legal_issue=false and still provide best-effort fields.
- Keep summary concise and practical.

User message:
{text}
"""

    try:
        text_output = call_gemini(prompt)
        parsed = extract_json_object(text_output)
        if not isinstance(parsed, dict):
            return fallback

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
        }
    except Exception:
        return fallback


def generate_chat_response(user_message: str, context: str = "") -> str:
    if not GEMINI_API_KEY:
        return "AI response is unavailable."

    final_prompt = user_message if not context else f"""
User question: {user_message}

Use the following professionals to answer:
{context}

Respond naturally and recommend the best options.
"""

    try:
        return call_gemini(final_prompt, timeout_seconds=25)
    except Exception:
        return "Sorry, I couldn’t generate a response."
