import asyncio
import logging

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from auth_utils import get_current_user_optional
from services.ai_service import analyze_legal_problem, generate_chat_response
from services.matching_service import rank_lawyers

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    user_id: int | None = None


def _rate_limit_actor_key(request: Request, current_user: dict | None) -> str:
    # Rate limiting must be keyed on something the caller can't spoof.
    # A verified JWT identity is preferred; until auth is enforced on this
    # route, fall back to the client IP rather than any client-supplied
    # user_id, which can be rotated per-request to bypass the limit.
    if current_user is not None and current_user.get("sub") is not None:
        return f"user:{current_user['sub']}"
    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


@router.post("/chat")
async def chat(
    data: ChatRequest,
    request: Request,
    current_user: dict | None = Depends(get_current_user_optional),
):
    message = data.message.strip()
    actor_key = _rate_limit_actor_key(request, current_user)
    if not message:
        return {
            "response": "Please describe your legal problem.",
            "analysis": None,
            "suggested_lawyers": [],
            "can_post_case": False,
        }

    # analyze_legal_problem/generate_chat_response make blocking HTTP calls;
    # run them off the event loop so one slow chat request doesn't stall
    # every other concurrent request on this server.
    analysis = await asyncio.to_thread(analyze_legal_problem, message, actor_key=actor_key)
    case_intelligence = None
    legal_area = analysis.get("legal_area") if isinstance(analysis, dict) else None
    location = analysis.get("location") if isinstance(analysis, dict) else None

    lawyers = []
    try:
        lawyers = rank_lawyers(
            query_text=message,
            legal_area=legal_area,
            city=location,
            limit=3,
        )
    except Exception as exc:
        # Keep chat available even when the ranking DB path is unavailable.
        logger.warning("Lawyer ranking unavailable for chat request: %s", exc)

    context = ""
    if lawyers:
        context = "Top matching professionals:\n"
        for item in lawyers:
            context += (
                f"- {item['name']} in {item['city']}, rating {item['rating']} "
                f"({item['reviews']} reviews)\n"
            )

    response_text = await asyncio.to_thread(generate_chat_response, message, context, actor_key=actor_key)

    return {
        "response": response_text,
        "analysis": analysis,
        "case_intelligence": case_intelligence,
        "suggested_lawyers": lawyers,
        "can_post_case": bool(analysis.get("is_legal_issue", False)) if isinstance(analysis, dict) else False,
    }
