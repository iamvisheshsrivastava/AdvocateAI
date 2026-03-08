from fastapi import APIRouter

from models.legal_action import LegalActionGuideRequest
from services.legal_action_service import build_legal_action_guide

router = APIRouter(tags=["legal-actions"])


@router.post("/legal-action-guide")
async def legal_action_guide(data: LegalActionGuideRequest):
    return build_legal_action_guide(data.problem_description)