from fastapi import APIRouter, File, HTTPException, UploadFile

from services.document_analysis_service import analyze_document
from services.matching_service import rank_lawyers

router = APIRouter(tags=["documents"])


@router.post("/documents/analyze")
async def analyze_uploaded_document(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        analysis = analyze_document(file.filename or "document", file.content_type, file_bytes)

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

        return {
            "document_type": analysis.get("document_type", "Unknown"),
            "legal_area": analysis.get("legal_area", "General Legal"),
            "key_dates": analysis.get("key_dates", []),
            "summary": analysis.get("summary", ""),
            "potential_issue": analysis.get("potential_issue", ""),
            "recommended_action": analysis.get("recommended_action", ""),
            "recommended_lawyers": recommended,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to analyze document.") from exc
