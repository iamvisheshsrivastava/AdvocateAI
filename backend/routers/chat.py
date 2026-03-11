from fastapi import APIRouter
from pydantic import BaseModel
from services.ai_service import analyze_legal_problem, generate_chat_response
from services.case_intelligence_service import build_case_intelligence
from services.matching_service import rank_lawyers

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    user_id: int | None = None


@router.post("/chat")
async def chat(data: ChatRequest):
    message = data.message.strip()
    actor_key = f"user:{data.user_id}" if data.user_id is not None else "anonymous"
    if not message:
        return {
            "response": "Please describe your legal problem.",
            "analysis": None,
            "suggested_lawyers": [],
            "can_post_case": False,
        }

    analysis = analyze_legal_problem(message, actor_key=actor_key)
    case_intelligence = build_case_intelligence(
        problem_text=message,
        analysis=analysis,
        case_brief=analysis.get("case_brief") if isinstance(analysis, dict) else None,
        actor_key=actor_key,
    )
    lawyers = rank_lawyers(
        query_text=message,
        legal_area=analysis.get("legal_area"),
        city=analysis.get("location"),
        limit=3,
    )

    context = ""
    if lawyers:
        context = "Top matching professionals:\n"
        for item in lawyers:
            context += (
                f"- {item['name']} in {item['city']}, rating {item['rating']} "
                f"({item['reviews']} reviews)\n"
            )

    response_text = generate_chat_response(message, context, actor_key=actor_key)

    return {
        "response": response_text,
        "analysis": analysis,
        "case_intelligence": case_intelligence,
        "suggested_lawyers": lawyers,
        "can_post_case": bool(analysis.get("is_legal_issue", False)),
    }
