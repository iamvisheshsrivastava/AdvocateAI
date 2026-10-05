"""Stripe payment integration for the Premium subscription flow (issue #12).

This module is written to be real and correct against Stripe's API, but it
fails safe (``enabled: False``) whenever the required environment variables
are not configured -- which is the case in this deployment today, since no
live or test Stripe keys have been provided. No key is ever fabricated here.

Required env vars to go live:
  - STRIPE_SECRET_KEY        Stripe secret key (sk_test_... or sk_live_...)
  - STRIPE_WEBHOOK_SECRET    Signing secret for the webhook endpoint (whsec_...)
  - STRIPE_PRICE_<PLAN>      Price id for each plan, e.g. STRIPE_PRICE_PRO=price_123

The `stripe` package is imported lazily (only once a secret key is present)
so the rest of the app keeps working even if the dependency isn't installed
yet in a given environment.
"""
from __future__ import annotations

import os
from typing import Any

from db.database import get_db_connection
from logging_config import get_logger

logger = get_logger(__name__)

_SUPPORTED_PLANS = ("basic", "pro", "premium")


def _get_secret_key() -> str | None:
    value = os.getenv("STRIPE_SECRET_KEY")
    return value.strip() if value and value.strip() else None


def _get_webhook_secret() -> str | None:
    value = os.getenv("STRIPE_WEBHOOK_SECRET")
    return value.strip() if value and value.strip() else None


def _get_price_id(plan: str) -> str | None:
    value = os.getenv(f"STRIPE_PRICE_{plan.strip().upper()}")
    return value.strip() if value and value.strip() else None


def is_configured() -> bool:
    return _get_secret_key() is not None


def _stripe_module():
    """Lazily import and configure the `stripe` SDK.

    Only called once we already know STRIPE_SECRET_KEY is set, so importing
    the dependency is only required for a deployment that actually enables
    payments.
    """
    import stripe  # local import: optional dependency until keys are configured

    stripe.api_key = _get_secret_key()
    return stripe


def create_checkout_session(
    user_id: int,
    plan: str,
    success_url: str,
    cancel_url: str,
) -> dict[str, Any]:
    """Create a Stripe Checkout session for the given user/plan.

    Returns ``{"enabled": False, "reason": ...}`` without talking to Stripe
    at all if STRIPE_SECRET_KEY (or a price id for the plan) isn't set.
    """
    plan = (plan or "").strip().lower()
    if plan not in _SUPPORTED_PLANS:
        return {"enabled": False, "reason": f"Unknown plan '{plan}'."}

    secret_key = _get_secret_key()
    if not secret_key:
        return {
            "enabled": False,
            "reason": "Payments are not configured yet. STRIPE_SECRET_KEY is not set.",
        }

    price_id = _get_price_id(plan)
    if not price_id:
        return {
            "enabled": False,
            "reason": f"No Stripe price configured for plan '{plan}' (set STRIPE_PRICE_{plan.upper()}).",
        }

    try:
        stripe = _stripe_module()
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=str(user_id),
            metadata={"user_id": str(user_id), "plan": plan},
        )
        return {"enabled": True, "checkout_url": session.url, "session_id": session.id}
    except Exception as exc:  # pragma: no cover - network/Stripe errors
        logger.exception("Stripe checkout session creation failed")
        return {"enabled": True, "error": str(exc)}


def _set_user_subscription(user_id: int, tier: str, status: str) -> None:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE users
            SET subscription_tier = %s, subscription_status = %s
            WHERE id = %s
            """,
            (tier, status, user_id),
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()


def handle_webhook_event(payload: bytes, signature_header: str | None) -> dict[str, Any]:
    """Verify and process a Stripe webhook event.

    Returns ``{"enabled": False, ...}`` without attempting signature
    verification if STRIPE_WEBHOOK_SECRET isn't set.
    """
    webhook_secret = _get_webhook_secret()
    if not webhook_secret or not is_configured():
        return {
            "enabled": False,
            "reason": "Webhook handling is not configured yet. "
            "STRIPE_SECRET_KEY/STRIPE_WEBHOOK_SECRET are not set.",
        }

    stripe = _stripe_module()
    try:
        event = stripe.Webhook.construct_event(payload, signature_header, webhook_secret)
    except Exception as exc:
        logger.warning("Rejected Stripe webhook: invalid signature (%s)", exc)
        return {"enabled": True, "success": False, "error": "Invalid signature"}

    event_type = event.get("type")
    data_object = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        user_id = data_object.get("client_reference_id") or (data_object.get("metadata") or {}).get("user_id")
        plan = (data_object.get("metadata") or {}).get("plan", "premium")
        if user_id:
            _set_user_subscription(int(user_id), plan, "active")
    elif event_type == "payment_intent.succeeded":
        user_id = (data_object.get("metadata") or {}).get("user_id")
        plan = (data_object.get("metadata") or {}).get("plan", "premium")
        if user_id:
            _set_user_subscription(int(user_id), plan, "active")
    elif event_type in ("customer.subscription.deleted", "invoice.payment_failed"):
        user_id = (data_object.get("metadata") or {}).get("user_id")
        if user_id:
            _set_user_subscription(int(user_id), "free", "inactive")

    return {"enabled": True, "success": True, "type": event_type}
