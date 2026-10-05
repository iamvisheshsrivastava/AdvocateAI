from fastapi import APIRouter, Depends, HTTPException, Request

from auth_utils import get_current_user
from logging_config import get_logger
from models.payment import CreateCheckoutSessionRequest
from services.payment_service import create_checkout_session, handle_webhook_event

logger = get_logger(__name__)

router = APIRouter(tags=["payments"])


def _require_self(current_user: dict, user_id: int, message: str) -> None:
    if str(current_user.get("sub")) != str(user_id):
        raise HTTPException(status_code=403, detail=message)


@router.post("/payments/create-checkout-session")
async def create_checkout_session_endpoint(
    data: CreateCheckoutSessionRequest, current_user: dict = Depends(get_current_user)
):
    _require_self(current_user, data.user_id, "You can only start checkout for your own account.")
    result = create_checkout_session(
        user_id=data.user_id,
        plan=data.plan,
        success_url=data.success_url,
        cancel_url=data.cancel_url,
    )
    return result


@router.post("/payments/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    signature_header = request.headers.get("stripe-signature")
    result = handle_webhook_event(payload, signature_header)
    if not result.get("enabled", False):
        # Fail safe, not an error: payments simply aren't configured yet.
        return result
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "Webhook rejected."))
    return result
