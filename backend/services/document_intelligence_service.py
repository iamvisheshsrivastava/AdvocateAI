import base64
import io
import json
import uuid
import time
from dataclasses import dataclass
from typing import Any

import pdfplumber
import requests
from dotenv import load_dotenv
from pydantic import PrivateAttr

from db.database import get_db_connection
from services.ai_service import (
    GEMINI_API_KEY,
    LEGAL_DEFAULT_AREA,
    AI_CONFIG,
    build_case_brief,
    call_gemini,
    embed_model,
    extract_json_object,
)
from services.cache_service import cache_service
from services.mlops_service import get_ai_config, log_ai_event

load_dotenv()
from logging_config import get_logger

logger = get_logger(__name__)

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}

try:
    import fitz  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    fitz = None

try:
    from langchain.prompts import PromptTemplate
except Exception:  # pragma: no cover - optional dependency
    class PromptTemplate:  # type: ignore[no-redef]
        def __init__(self, template: str):
            self.template = template

        @classmethod
        def from_template(cls, template: str):
            return cls(template)

        def format(self, **kwargs):
            return self.template.format(**kwargs)


try:
    from llama_index.core import Document, VectorStoreIndex
    from llama_index.core.embeddings import BaseEmbedding
except Exception:  # pragma: no cover - optional dependency
    Document = None
    VectorStoreIndex = None
    BaseEmbedding = object


@dataclass
class ParsedDocument:
    file_name: str
    content_type: str | None
    extracted_text: str
    structured_extraction: dict[str, Any]
    page_count: int | None = None


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(normalized)
    return deduped


def _safe_str(value: Any, fallback: str = "") -> str:
    text = str(value or fallback).strip()
    return text if text else fallback


class SentenceTransformerEmbedding(BaseEmbedding):
    _backend_model: Any = PrivateAttr()

    def __init__(self, backend_model: Any):
        super().__init__()
        self._backend_model = backend_model

    @classmethod
    def class_name(cls) -> str:
        return "sentence_transformer_embedding"

    def _embed(self, text: str) -> list[float]:
        vector = self._backend_model.encode(text)
        return vector.tolist() if hasattr(vector, "tolist") else list(vector)

    def _get_query_embedding(self, query: str) -> list[float]:
        return self._embed(query)

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return self._embed(query)

    def _get_text_embedding(self, text: str) -> list[float]:
        return self._embed(text)

    async def _aget_text_embedding(self, text: str) -> list[float]:
        return self._embed(text)


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
        "structured_extraction": {
            "parties": [],
            "deadlines": [],
            "amounts": [],
            "obligations": [],
            "risks": [],
        },
        "retrieved_snippets": [],
    }


def _fallback_qa(question: str) -> dict[str, Any]:
    return {
        "question": question,
        "answer": "I could not retrieve a reliable answer from the uploaded documents.",
        "confidence_level": "Low",
        "supporting_documents": [],
        "retrieved_snippets": [],
        "follow_up_questions": [],
    }


def _extract_text_from_pdf(file_bytes: bytes) -> tuple[str, int]:
    if fitz is not None:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            pages_text: list[str] = []
            for page_index, page in enumerate(doc, start=1):
                page_text = page.get_text("text") or ""
                if not page_text.strip():
                    continue
                pages_text.append(f"[Page {page_index}]\n{page_text.strip()}")
            combined = "\n\n".join(pages_text)
            return combined[:20000], len(doc)
        except Exception as exc:
            logger.exception("fitz PDF extraction failed, falling back to pdfplumber: %s", exc)

    pages_text: list[str] = []
    page_count = 0
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        page_count = len(pdf.pages)
        for index, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages_text.append(f"[Page {index}]\n{text.strip()}")

    combined = "\n\n".join(pages_text)
    return combined[:20000], page_count


def _analysis_prompt_from_text(text: str) -> str:
    return f"""
Analyze the following legal document and return STRICT JSON only.

Use this schema exactly:
{{
  "document_type": "...",
  "legal_area": "...",
  "key_dates": ["..."],
  "summary": "...",
  "potential_issue": "...",
  "recommended_action": "...",
  "confidence_level": "Low|Medium|High",
  "citations": ["..."],
  "structured_extraction": {{
    "parties": ["..."],
    "deadlines": ["..."],
    "amounts": ["..."],
    "obligations": ["..."],
    "risks": ["..."]
  }}
}}

Rules:
- Keep the output concise and factual.
- Preserve dates, amounts, and obligations when they are explicitly stated.
- If the document is a letter, notice, contract, invoice, form, or court filing, say so.
- When details are missing, use empty arrays and avoid speculation.

Document content:
{text}
"""


def _analysis_prompt_for_image() -> str:
    return """
Analyze this legal document image and return STRICT JSON only.

Use this schema exactly:
{
  "document_type": "...",
  "legal_area": "...",
  "key_dates": ["..."],
  "summary": "...",
  "potential_issue": "...",
  "recommended_action": "...",
  "confidence_level": "Low|Medium|High",
  "citations": ["..."],
  "structured_extraction": {
    "parties": ["..."],
    "deadlines": ["..."],
    "amounts": ["..."],
    "obligations": ["..."],
    "risks": ["..."]
  }
}

Rules:
- Extract text directly from the visible layout when possible.
- Preserve any names, amounts, dates, and obligations that are visible.
- Keep the output concise and factual.
"""


def _qa_prompt_template() -> PromptTemplate:
    return PromptTemplate.from_template(
        """
You are a legal document QA assistant for uploaded client documents.
Answer only from the provided context and cite the context snippets you used.

Return STRICT JSON only with this schema:
{
  "question": "...",
  "answer": "...",
  "confidence_level": "Low|Medium|High",
  "supporting_documents": ["..."],
  "retrieved_snippets": [
    {
      "file_name": "...",
      "page": 1,
      "snippet": "..."
    }
  ],
  "follow_up_questions": ["..."]
}

Question:
{question}

Document context:
{context}

Document metadata:
{metadata}
"""
    )


def _normalize_confidence_level(value: str | None) -> str:
    normalized = (value or "medium").strip().lower()
    if normalized in ("low", "medium", "high"):
        return normalized.capitalize()
    return "Medium"


def _normalize_analysis(raw: dict[str, Any], file_name: str, page_count: int | None) -> dict[str, Any]:
    fallback = _fallback_analysis()
    structured = raw.get("structured_extraction") if isinstance(raw.get("structured_extraction"), dict) else {}

    key_dates = raw.get("key_dates", [])
    if not isinstance(key_dates, list):
        key_dates = [str(key_dates)]

    return {
        "document_type": _safe_str(raw.get("document_type"), fallback["document_type"]),
        "legal_area": _safe_str(raw.get("legal_area"), fallback["legal_area"]),
        "file_name": file_name,
        "page_count": page_count,
        "key_dates": [str(item).strip() for item in key_dates if str(item).strip()],
        "summary": _safe_str(raw.get("summary"), fallback["summary"]),
        "potential_issue": _safe_str(raw.get("potential_issue"), fallback["potential_issue"]),
        "recommended_action": _safe_str(raw.get("recommended_action"), fallback["recommended_action"]),
        "confidence_level": _normalize_confidence_level(raw.get("confidence_level")),
        "citations": [str(item).strip() for item in raw.get("citations", []) if str(item).strip()],
        "structured_extraction": {
            "parties": _dedupe(_as_list(structured.get("parties"))),
            "deadlines": _dedupe(_as_list(structured.get("deadlines"))),
            "amounts": _dedupe(_as_list(structured.get("amounts"))),
            "obligations": _dedupe(_as_list(structured.get("obligations"))),
            "risks": _dedupe(_as_list(structured.get("risks"))),
        },
    }


def _build_llamaindex_index(records: list[dict[str, Any]]):
    if Document is None or VectorStoreIndex is None:
        return None

    documents: list[Any] = []
    for record in records:
        extracted_text = _safe_str(record.get("extracted_text"))
        if not extracted_text:
            continue

        documents.append(
            Document(
                text=extracted_text,
                metadata={
                    "document_id": record.get("id"),
                    "batch_id": record.get("batch_id"),
                    "file_name": record.get("file_name"),
                    "page_count": record.get("page_count"),
                    "document_type": record.get("document_type"),
                },
            )
        )

    if not documents:
        return None

    return VectorStoreIndex.from_documents(
        documents,
        embed_model=SentenceTransformerEmbedding(embed_model),
    )


def _retrieve_snippets(records: list[dict[str, Any]], question_or_summary: str, top_k: int = 3) -> list[dict[str, Any]]:
    index = _build_llamaindex_index(records)
    if index is None:
        return []

    retriever = index.as_retriever(similarity_top_k=top_k)
    try:
        nodes = retriever.retrieve(question_or_summary)
    except Exception:
        logger.exception("LlamaIndex retrieval failed")
        return []

    snippets: list[dict[str, Any]] = []
    for item in nodes:
        node = getattr(item, "node", None)
        if node is None:
            continue
        metadata = getattr(node, "metadata", {}) or {}
        snippets.append(
            {
                "file_name": metadata.get("file_name") or "document",
                "document_id": metadata.get("document_id"),
                "page": metadata.get("page") or metadata.get("page_count"),
                "score": round(float(getattr(item, "score", 0.0) or 0.0), 4),
                "snippet": _safe_str(node.get_text(), "")[:500],
            }
        )

    return snippets


def _extract_textual_analysis(text: str, file_name: str, page_count: int | None) -> dict[str, Any]:
    if not text.strip():
        return _fallback_analysis()

    prompt = _analysis_prompt_from_text(text)
    response_text = call_gemini(
        prompt,
        timeout_seconds=AI_CONFIG.analysis_timeout_seconds,
        telemetry={
            "event_name": "document_text_analysis",
            "document_name": file_name,
            "page_count": page_count or 0,
            "input_length": len(text),
        },
    )
    parsed = extract_json_object(response_text)
    if not isinstance(parsed, dict) or not parsed:
        return _fallback_analysis()
    return _normalize_analysis(parsed, file_name=file_name, page_count=page_count)


def _extract_image_analysis(file_bytes: bytes, mime_type: str, file_name: str) -> dict[str, Any]:
    if not GEMINI_API_KEY:
        return _fallback_analysis()

    started_at = time.perf_counter()
    ai_config = get_ai_config()
    encoded = base64.b64encode(file_bytes).decode("utf-8")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{ai_config.gemini_model}:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": _analysis_prompt_for_image()},
                    {"inlineData": {"mimeType": mime_type, "data": encoded}},
                ]
            }
        ]
    }

    try:
        response = requests.post(url, json=payload, timeout=ai_config.document_timeout_seconds)
        response.raise_for_status()
        result = response.json()
        response_text = result["candidates"][0]["content"]["parts"][0]["text"]
        log_ai_event(
            "document_image_analysis",
            started_at=started_at,
            status="success",
            input_text=file_name,
            output_text=response_text,
            actor_key="document_image",
            model_name=ai_config.gemini_model,
            metadata={"mime_type": mime_type, "file_name": file_name},
        )
    except Exception as exc:
        log_ai_event(
            "document_image_analysis",
            started_at=started_at,
            status="error",
            input_text=file_name,
            output_text="",
            actor_key="document_image",
            model_name=ai_config.gemini_model,
            metadata={"mime_type": mime_type, "file_name": file_name},
            error=exc,
        )
        raise

    parsed = extract_json_object(response_text)
    if not isinstance(parsed, dict) or not parsed:
        return _fallback_analysis()
    return _normalize_analysis(parsed, file_name=file_name, page_count=None)


def _extract_document(file_name: str, content_type: str | None, file_bytes: bytes) -> ParsedDocument:
    extension = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported file type. Only PDF, JPG, JPEG, and PNG are allowed.")

    if extension == "pdf":
        extracted_text, page_count = _extract_text_from_pdf(file_bytes)
        structured = _extract_textual_analysis(extracted_text, file_name=file_name, page_count=page_count)
        return ParsedDocument(
            file_name=file_name,
            content_type=content_type,
            extracted_text=extracted_text,
            structured_extraction=structured,
            page_count=page_count,
        )

    mime = content_type or ("image/png" if extension == "png" else "image/jpeg")
    structured = _extract_image_analysis(file_bytes, mime, file_name=file_name)
    extracted_text = structured.get("summary", "")
    return ParsedDocument(
        file_name=file_name,
        content_type=content_type,
        extracted_text=extracted_text,
        structured_extraction=structured,
        page_count=1,
    )


def _store_document_batch(
    parsed_documents: list[ParsedDocument],
    user_id: int | None,
    case_id: int | None,
) -> str:
    batch_id = uuid.uuid4().hex
    conn = get_db_connection()
    cur = conn.cursor()
    for item in parsed_documents:
        cur.execute(
            """
            INSERT INTO case_documents (
                batch_id, user_id, case_id, file_name, content_type, page_count,
                document_type, legal_area, extracted_text, structured_json, summary,
                potential_issue, recommended_action, confidence_level, citations
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s::jsonb)
            """,
            (
                batch_id,
                user_id,
                case_id,
                item.file_name,
                item.content_type,
                item.page_count,
                item.structured_extraction.get("document_type"),
                item.structured_extraction.get("legal_area"),
                item.extracted_text,
                json.dumps(item.structured_extraction, ensure_ascii=True),
                item.structured_extraction.get("summary"),
                item.structured_extraction.get("potential_issue"),
                item.structured_extraction.get("recommended_action"),
                item.structured_extraction.get("confidence_level"),
                json.dumps(item.structured_extraction.get("citations", []), ensure_ascii=True),
            ),
        )

    conn.commit()
    cur.close()
    conn.close()
    return batch_id


def _decode_json_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            logger.debug("Failed to decode JSON value for document field")
            return value
    return value


def _document_row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    structured_json = _decode_json_value(row[10]) or {}
    citations = _decode_json_value(row[15]) or []

    return {
        "id": row[0],
        "batch_id": row[1],
        "user_id": row[2],
        "case_id": row[3],
        "file_name": row[4],
        "content_type": row[5],
        "page_count": row[6],
        "document_type": row[7],
        "legal_area": row[8],
        "extracted_text": row[9] or "",
        "structured_json": structured_json,
        "summary": row[11] or "",
        "potential_issue": row[12] or "",
        "recommended_action": row[13] or "",
        "confidence_level": row[14] or "Low",
        "citations": citations,
        "created_at": str(row[16]),
    }


def _load_document_batch(batch_id: str) -> list[dict[str, Any]]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, batch_id, user_id, case_id, file_name, content_type, page_count,
               document_type, legal_area, extracted_text, structured_json, summary,
               potential_issue, recommended_action, confidence_level, citations, created_at
        FROM case_documents
        WHERE batch_id = %s
        ORDER BY id ASC
        """,
        (batch_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [_document_row_to_dict(row) for row in rows]


def _build_aggregate_analysis(documents: list[dict[str, Any]]) -> dict[str, Any]:
    if not documents:
        return _fallback_analysis()

    primary = documents[0]
    combined_summary = "\n".join([item.get("summary", "") for item in documents if item.get("summary")]).strip()
    combined_text = "\n".join([item.get("extracted_text", "") for item in documents if item.get("extracted_text")]).strip()

    retrieved_snippets = _retrieve_snippets(documents, combined_summary or combined_text)
    structured_extractions = [item.get("structured_json", {}) for item in documents]
    merged_structured = {
        "parties": _dedupe([value for item in structured_extractions for value in _as_list(item.get("parties"))]),
        "deadlines": _dedupe([value for item in structured_extractions for value in _as_list(item.get("deadlines"))]),
        "amounts": _dedupe([value for item in structured_extractions for value in _as_list(item.get("amounts"))]),
        "obligations": _dedupe([value for item in structured_extractions for value in _as_list(item.get("obligations"))]),
        "risks": _dedupe([value for item in structured_extractions for value in _as_list(item.get("risks"))]),
    }

    return {
        "document_type": "Multi-document packet" if len(documents) > 1 else primary.get("document_type", "Unknown"),
        "legal_area": primary.get("legal_area") or LEGAL_DEFAULT_AREA,
        "key_dates": _dedupe([date for item in documents for date in _as_list(item.get("structured_json", {}).get("deadlines"))]),
        "summary": combined_summary or primary.get("summary", ""),
        "potential_issue": primary.get("potential_issue", "Unknown"),
        "recommended_action": primary.get("recommended_action", ""),
        "confidence_level": primary.get("confidence_level", "Low"),
        "citations": _dedupe([citation for item in documents for citation in _as_list(item.get("citations"))]),
        "structured_extraction": merged_structured,
        "retrieved_snippets": retrieved_snippets,
        "documents": documents,
        "document_batch_id": primary.get("batch_id"),
    }


def analyze_document(
    file_name: str,
    content_type: str | None,
    file_bytes: bytes,
    actor_key: str = "anonymous",
    user_id: int | None = None,
    case_id: int | None = None,
) -> dict[str, Any]:
    cache_key = f"document_analysis:{cache_service.make_hash(file_name + str(len(file_bytes)) + file_bytes[:256].hex())}"
    cached = cache_service.get(cache_key)
    if cached:
        return cached

    parsed = _extract_document(file_name, content_type, file_bytes)
    batch_id = _store_document_batch([parsed], user_id=user_id, case_id=case_id)
    result = dict(parsed.structured_extraction)
    result["documents"] = [
        {
            "file_name": parsed.file_name,
            "content_type": parsed.content_type,
            "page_count": parsed.page_count,
            **parsed.structured_extraction,
        }
    ]
    result["document_batch_id"] = batch_id
    result["retrieved_snippets"] = _retrieve_snippets(
        [
            {
                "id": 1,
                "batch_id": batch_id,
                "file_name": parsed.file_name,
                "page_count": parsed.page_count,
                "document_type": parsed.structured_extraction.get("document_type"),
                "extracted_text": parsed.extracted_text,
            }
        ],
        parsed.structured_extraction.get("summary", parsed.extracted_text),
    )
    result["case_brief"] = build_case_brief(
        parsed.structured_extraction.get("summary", ""),
        analysis={
            "legal_area": parsed.structured_extraction.get("legal_area"),
            "summary": parsed.structured_extraction.get("summary"),
        },
        document_names=[file_name],
        actor_key=actor_key,
    )
    cache_service.set(cache_key, result, ttl_seconds=1800)
    return result


def analyze_documents(
    files: list[tuple[str, str | None, bytes]],
    actor_key: str = "anonymous",
    user_id: int | None = None,
    case_id: int | None = None,
) -> dict[str, Any]:
    if not files:
        raise ValueError("At least one document is required.")

    parsed_documents = [_extract_document(name, content_type, payload) for name, content_type, payload in files]
    batch_id = _store_document_batch(parsed_documents, user_id=user_id, case_id=case_id)

    documents_payload = []
    for parsed in parsed_documents:
        documents_payload.append(
            {
                "file_name": parsed.file_name,
                "content_type": parsed.content_type,
                "page_count": parsed.page_count,
                **parsed.structured_extraction,
            }
        )

    aggregate = _build_aggregate_analysis(
        [
            {
                "id": index + 1,
                "batch_id": batch_id,
                "file_name": parsed.file_name,
                "page_count": parsed.page_count,
                "document_type": parsed.structured_extraction.get("document_type"),
                "legal_area": parsed.structured_extraction.get("legal_area"),
                "summary": parsed.structured_extraction.get("summary"),
                "potential_issue": parsed.structured_extraction.get("potential_issue"),
                "recommended_action": parsed.structured_extraction.get("recommended_action"),
                "confidence_level": parsed.structured_extraction.get("confidence_level"),
                "citations": parsed.structured_extraction.get("citations", []),
                "structured_json": parsed.structured_extraction,
                "extracted_text": parsed.extracted_text,
            }
            for index, parsed in enumerate(parsed_documents)
        ]
    )

    aggregate["documents"] = documents_payload
    aggregate["document_batch_id"] = batch_id
    aggregate["case_brief"] = build_case_brief(
        aggregate.get("summary", ""),
        analysis={
            "legal_area": aggregate.get("legal_area"),
            "summary": aggregate.get("summary"),
        },
        document_names=[name for name, _, _ in files],
        actor_key=actor_key,
    )
    return aggregate


def answer_document_question(
    batch_id: str,
    question: str,
    actor_key: str = "anonymous",
) -> dict[str, Any]:
    if not question.strip():
        raise ValueError("A question is required.")

    documents = _load_document_batch(batch_id)
    if not documents:
        raise ValueError("No uploaded documents were found for this batch.")

    cache_key = f"document_qa:{cache_service.make_hash(batch_id + '::' + question)}"
    cached = cache_service.get(cache_key)
    if cached:
        return cached

    if not cache_service.allow_request("document_qa", actor_key, limit=25, window_seconds=60):
        fallback = _fallback_qa(question)
        fallback["rate_limited"] = True
        return fallback

    retrieved_snippets = _retrieve_snippets(documents, question)
    context = "\n\n".join(
        [
            f"Source: {item['file_name']} | Page: {item.get('page', 'n/a')}\n{item['snippet']}"
            for item in retrieved_snippets
        ]
    )

    metadata = json.dumps(
        [
            {
                "file_name": item["file_name"],
                "document_type": item.get("document_type"),
                "legal_area": item.get("legal_area"),
                "page_count": item.get("page_count"),
            }
            for item in documents
        ],
        ensure_ascii=True,
    )

    prompt = _qa_prompt_template().format(question=question, context=context, metadata=metadata)
    response_text = call_gemini(
        prompt,
        timeout_seconds=AI_CONFIG.document_timeout_seconds,
        telemetry={
            "event_name": "document_question_answering",
            "document_batch_size": len(documents),
            "question_length": len(question),
        },
    )
    parsed = extract_json_object(response_text)
    if not isinstance(parsed, dict) or not parsed:
        fallback = _fallback_qa(question)
        fallback["retrieved_snippets"] = retrieved_snippets
        fallback["supporting_documents"] = _dedupe([item["file_name"] for item in retrieved_snippets])
        return fallback

    answer = {
        "question": _safe_str(parsed.get("question"), question),
        "answer": _safe_str(parsed.get("answer"), ""),
        "confidence_level": _normalize_confidence_level(parsed.get("confidence_level")),
        "supporting_documents": _dedupe(_as_list(parsed.get("supporting_documents")))
        or _dedupe([item["file_name"] for item in retrieved_snippets]),
        "retrieved_snippets": retrieved_snippets,
        "follow_up_questions": _dedupe(_as_list(parsed.get("follow_up_questions"))),
        "document_batch_id": batch_id,
    }
    cache_service.set(cache_key, answer, ttl_seconds=900)
    return answer


def get_document_batch(batch_id: str) -> list[dict[str, Any]]:
    return _load_document_batch(batch_id)
