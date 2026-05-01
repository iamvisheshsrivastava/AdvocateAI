from typing import Annotated

from fastapi import APIRouter, Query

from logging_config import get_logger
from services.ml_matching_service import (
    get_model_status,
    recommend_lawyers_for_case_ml,
    train_lawyer_match_model,
)

router = APIRouter(tags=["ml"])
logger = get_logger(__name__)


@router.get("/ml/lawyer-matching/status")
async def lawyer_matching_status():
    return get_model_status()


@router.post("/ml/lawyer-matching/train")
async def train_lawyer_matching_model(
    max_negatives_per_case: Annotated[int, Query(ge=5, le=200)] = 20,
):
    try:
        manifest = train_lawyer_match_model(max_negatives_per_case=max_negatives_per_case)
        return {"success": True, "manifest": manifest}
    except Exception as exc:
        logger.exception("Failed to train lawyer matching model")
        return {"success": False, "error": str(exc)}


@router.get("/ml/lawyer-matching/recommend/{case_id}")
async def get_lawyer_matching_recommendations(
    case_id: int,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
):
    return recommend_lawyers_for_case_ml(case_id, limit=limit)
