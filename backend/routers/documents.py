from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from auth_utils import get_current_user_optional
from models.document import DocumentQuestionRequest
from services.case_intelligence_service import build_case_intelligence
from services.document_analysis_service import analyze_document, analyze_documents
from services.document_intelligence_service import answer_document_question
from services.matching_service import rank_lawyers
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["documents"])

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB per file


def _rate_limit_actor_key(request: Request, current_user: dict | None) -> str:
    # Rate limiting must be keyed on something the caller can't spoof.
    # A verified JWT identity is preferred; until auth is enforced on these
    # routes, fall back to the client IP rather than any client-supplied
    # user_id, which can be rotated per-request to bypass the limit.
    if current_user is not None and current_user.get("sub") is not None:
        return f"user:{current_user['sub']}"
    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


@router.post(
    "/documents/analyze",
    responses={
        400: {"description": "Invalid or empty upload."},
        500: {"description": "Document analysis failed."},
    },
)
async def analyze_uploaded_document(
    request: Request,
    file: Annotated[UploadFile | None, File()] = None,
    files: Annotated[list[UploadFile] | None, File()] = None,
    user_id: Annotated[int | None, Form()] = None,
    current_user: dict | None = Depends(get_current_user_optional),
):
    try:
        uploads = [item for item in (files or []) if item is not None]
        if file is not None:
            uploads.insert(0, file)
        if not uploads:
            raise HTTPException(status_code=400, detail="At least one file is required.")

        payloads: list[tuple[str, str | None, bytes]] = []
        for upload in uploads:
            # Read one byte past the cap so we can detect an oversized file
            # without buffering the whole thing into memory first.
            file_bytes = await upload.read(MAX_FILE_SIZE_BYTES + 1)
            if len(file_bytes) > MAX_FILE_SIZE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"'{upload.filename or 'file'}' exceeds the 10 MB upload limit.",
                )
            if not file_bytes:
                continue
            payloads.append((upload.filename or "document", upload.content_type, file_bytes))

        if not payloads:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        actor_key = _rate_limit_actor_key(request, current_user)
        analysis = (
            analyze_documents(payloads, actor_key=actor_key, user_id=user_id)
            if len(payloads) > 1
            else analyze_document(
                payloads[0][0],
                payloads[0][1],
                payloads[0][2],
                actor_key=actor_key,
                user_id=user_id,
            )
        )

        query = (
            f"{analysis.get('document_type', '')} "
            f"{analysis.get('legal_area', '')} "
            f"{analysis.get('summary', '')} "
            f"{analysis.get('potential_issue', '')}"
        ).strip()

        recommended = rank_lawyers(
            query_text=query,
            legal_area=analysis.get("legal_area"),
            limit=5,
        )
        case_intelligence = build_case_intelligence(
            problem_text=analysis.get("summary", ""),
            analysis=analysis,
            case_brief=analysis.get("case_brief") if isinstance(analysis.get("case_brief"), dict) else None,
            document_names=[name for name, _, _ in payloads],
            actor_key=actor_key,
        )

        return {
            "document_batch_id": analysis.get("document_batch_id"),
            "document_type": analysis.get("document_type", "Unknown"),
            "legal_area": analysis.get("legal_area", "General Legal"),
            "key_dates": analysis.get("key_dates", []),
            "summary": analysis.get("summary", ""),
            "potential_issue": analysis.get("potential_issue", ""),
            "recommended_action": analysis.get("recommended_action", ""),
            "confidence_level": analysis.get("confidence_level", "Low"),
            "citations": analysis.get("citations", []),
            "structured_extraction": analysis.get("structured_extraction", {}),
            "retrieved_snippets": analysis.get("retrieved_snippets", []),
            "case_brief": analysis.get("case_brief", {}),
            "documents": analysis.get("documents", []),
            "case_intelligence": case_intelligence,
            "recommended_lawyers": recommended,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to analyze uploaded document")
        raise HTTPException(status_code=500, detail="Failed to analyze document.") from exc


@router.post(
    "/documents/qa",
    responses={
        400: {"description": "Question or batch ID missing."},
        404: {"description": "No uploaded documents found for the batch."},
        500: {"description": "Document QA failed."},
    },
)
async def ask_document_question(
    request: DocumentQuestionRequest,
    http_request: Request,
    current_user: dict | None = Depends(get_current_user_optional),
):
    try:
        answer = answer_document_question(
            batch_id=request.document_batch_id,
            question=request.question,
            actor_key=_rate_limit_actor_key(http_request, current_user),
        )
        return answer
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to answer document question")
        raise HTTPException(status_code=500, detail="Failed to answer document question.") from exc
