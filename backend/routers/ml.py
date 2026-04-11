from fastapi import APIRouter, Query

from services.ml_matching_service import (
    get_model_status,
    recommend_lawyers_for_case_ml,
    train_lawyer_match_model,
)

router = APIRouter(tags=["ml"])


@router.get("/ml/lawyer-matching/status")
async def lawyer_matching_status():
    return get_model_status()


@router.post("/ml/lawyer-matching/train")
async def train_lawyer_matching_model(
    max_negatives_per_case: int = Query(default=20, ge=5, le=200),
):
    try:
        manifest = train_lawyer_match_model(max_negatives_per_case=max_negatives_per_case)
        return {"success": True, "manifest": manifest}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@router.get("/ml/lawyer-matching/recommend/{case_id}")
async def get_lawyer_matching_recommendations(case_id: int, limit: int = Query(default=5, ge=1, le=20)):
    return recommend_lawyers_for_case_ml(case_id, limit=limit)
