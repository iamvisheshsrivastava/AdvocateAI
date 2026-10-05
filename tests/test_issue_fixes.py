from __future__ import annotations

import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth_utils import create_access_token
from routers import cases as cases_module
from routers import lawyers as lawyers_module
from routers.auth import _normalize_role
from routers.cases import router as cases_router
from routers.lawyers import router as lawyers_router
from services import deadline_reminder_service, matching_service, payment_service


class ScriptedCursor:
    """A fake DB cursor that returns canned fetchone/fetchall results in order."""

    def __init__(self, fetchone_results=None, fetchall_results=None):
        self._fetchone_iter = iter(fetchone_results or [])
        self._fetchall_iter = iter(fetchall_results or [])
        self.executed = []
        self.closed = False

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchone(self):
        return next(self._fetchone_iter, None)

    def fetchall(self):
        return next(self._fetchall_iter, [])

    def close(self):
        self.closed = True


class ScriptedConnection:
    def __init__(self, cursor: ScriptedCursor):
        self._cursor = cursor
        self.committed = 0
        self.rolled_back = 0
        self.closed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed += 1

    def rollback(self):
        self.rolled_back += 1

    def close(self):
        self.closed = True


def _fail_if_called(*_args, **_kwargs):
    raise AssertionError("should not have been called")


# ---------------------------------------------------------------------------
# Issue #28: signup must never be able to self-assign the admin role.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw_role,expected",
    [
        ("admin", "client"),
        ("Admin", "client"),
        ("  ADMIN  ", "client"),
        ("lawyer", "lawyer"),
        ("client", "client"),
        (None, "client"),
        ("superuser", "client"),
    ],
)
def test_normalize_role_rejects_anything_but_client_or_lawyer(raw_role, expected):
    assert _normalize_role(raw_role) == expected


# ---------------------------------------------------------------------------
# Issue #27: refresh_lawyer_responsiveness must lock the row (SELECT ... FOR
# UPDATE) and do the read+write inside a single transaction instead of a
# plain read-then-write.
# ---------------------------------------------------------------------------


def test_refresh_lawyer_responsiveness_locks_row_and_commits_once(monkeypatch):
    cursor = ScriptedCursor(fetchone_results=[(4.0, 2, 1)])
    conn = ScriptedConnection(cursor)
    monkeypatch.setattr(matching_service, "get_db_connection", lambda: conn)

    matching_service.refresh_lawyer_responsiveness(
        lawyer_id=42, increment_applications=True, response_time_hours=2.0
    )

    select_query = cursor.executed[0][0]
    assert "FOR UPDATE" in select_query
    assert conn.committed == 1
    assert conn.rolled_back == 0
    assert conn.closed is True

    update_query, update_params = cursor.executed[1]
    assert "UPDATE lawyer_profiles" in update_query
    # applications_sent incremented from 2 -> 3, response_time averaged (4+2)/2=3.0
    assert update_params[1] == 3
    assert update_params[0] == 3.0


def test_refresh_lawyer_responsiveness_rolls_back_when_lawyer_missing(monkeypatch):
    cursor = ScriptedCursor(fetchone_results=[None])
    conn = ScriptedConnection(cursor)
    monkeypatch.setattr(matching_service, "get_db_connection", lambda: conn)

    matching_service.refresh_lawyer_responsiveness(lawyer_id=999, increment_applications=True)

    assert conn.rolled_back == 1
    assert conn.committed == 0
    assert not any("UPDATE lawyer_profiles" in q for q, _ in cursor.executed)


# ---------------------------------------------------------------------------
# Issue #24: lawyer availability slots + booking.
# ---------------------------------------------------------------------------


def _lawyers_app() -> TestClient:
    app = FastAPI()
    app.include_router(lawyers_router)
    return TestClient(app)


def test_book_availability_slot_success(monkeypatch):
    cursor = ScriptedCursor(
        fetchone_results=[
            (5,),  # case client_id lookup -> client_id == caller, participant
            (42, False),  # slot: lawyer_id, is_booked
            (1,),  # lawyer has an application on this case
            (7, "2026-11-01 10:00:00", "2026-11-01 10:30:00"),  # UPDATE ... RETURNING
        ],
    )

    class _BookingConnection(ScriptedConnection):
        def cursor(self):
            return cursor

    conn = _BookingConnection(cursor)
    monkeypatch.setattr(lawyers_module, "get_db_connection", lambda: conn)
    monkeypatch.setattr(lawyers_module, "create_notification", lambda **kwargs: None)
    monkeypatch.setattr(lawyers_module, "publish_case_message", lambda *args, **kwargs: None)

    client = _lawyers_app()
    token = create_access_token(user_id=5, role="client", email="client5@example.com")
    response = client.post(
        "/lawyer/availability/book",
        json={"slot_id": 7, "client_id": 5, "case_id": 3},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["lawyer_id"] == 42
    assert conn.committed == 1


def test_book_availability_slot_rejects_already_booked(monkeypatch):
    cursor = ScriptedCursor(fetchone_results=[(5,), (42, True)])

    class _BookingConnection(ScriptedConnection):
        def cursor(self):
            return cursor

    conn = _BookingConnection(cursor)
    monkeypatch.setattr(lawyers_module, "get_db_connection", lambda: conn)
    monkeypatch.setattr(lawyers_module, "create_notification", _fail_if_called)
    monkeypatch.setattr(lawyers_module, "publish_case_message", _fail_if_called)

    client = _lawyers_app()
    token = create_access_token(user_id=5, role="client", email="client5@example.com")
    response = client.post(
        "/lawyer/availability/book",
        json={"slot_id": 7, "client_id": 5, "case_id": 3},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert "already been booked" in body["message"]
    assert conn.rolled_back == 1


def test_book_availability_slot_rejects_non_owner_client(monkeypatch):
    cursor = ScriptedCursor(fetchone_results=[(99,)])  # case belongs to a different client
    conn = ScriptedConnection(cursor)
    monkeypatch.setattr(lawyers_module, "get_db_connection", lambda: conn)
    monkeypatch.setattr(lawyers_module, "create_notification", _fail_if_called)
    monkeypatch.setattr(lawyers_module, "publish_case_message", _fail_if_called)

    client = _lawyers_app()
    token = create_access_token(user_id=5, role="client", email="client5@example.com")
    response = client.post(
        "/lawyer/availability/book",
        json={"slot_id": 7, "client_id": 5, "case_id": 3},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Issue #23: consultation packet PDF export.
# ---------------------------------------------------------------------------


def test_consultation_packet_pdf_for_case_owner(monkeypatch):
    case_row = (
        3,  # case_id
        5,  # client_id
        "Noisy neighbor dispute",  # title
        "My neighbor plays loud music every night.",  # description
        "Tenant Dispute",  # legal_area
        "Noise Complaint",  # issue_type
        "Client reports repeated noise disturbances.",  # ai_summary
        "Medium",  # urgency
        "Berlin",  # city
        {},  # case_brief
        "2026-10-01 00:00:00",  # created_at
        "open",  # status
        True,  # is_public
    )
    cursor = ScriptedCursor(fetchone_results=[case_row])
    conn = ScriptedConnection(cursor)
    monkeypatch.setattr(cases_module, "get_db_connection", lambda: conn)

    app = FastAPI()
    app.include_router(cases_router)
    client = TestClient(app)
    token = create_access_token(user_id=5, role="client", email="client5@example.com")

    response = client.get(
        "/cases/3/consultation-packet.pdf",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_consultation_packet_pdf_forbidden_for_non_participant(monkeypatch):
    case_row = (
        3,
        5,
        "Title",
        "Description",
        "Area",
        "Issue",
        "Summary",
        "Medium",
        "Berlin",
        {},
        "2026-10-01 00:00:00",
        "open",
        True,
    )
    cursor = ScriptedCursor(fetchone_results=[case_row, None])
    conn = ScriptedConnection(cursor)
    monkeypatch.setattr(cases_module, "get_db_connection", lambda: conn)

    app = FastAPI()
    app.include_router(cases_router)
    client = TestClient(app)
    token = create_access_token(user_id=999, role="client", email="other@example.com")

    response = client.get(
        "/cases/3/consultation-packet.pdf",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Issue #22: proactive deadline reminders.
# ---------------------------------------------------------------------------


def test_scan_and_notify_deadlines_sends_once_per_threshold(monkeypatch):
    case_row = (
        3,  # case_id
        5,  # client_id
        "Title",
        "Description",
        "Area",
        "Issue",
        None,
        "Medium",
        "Berlin",
        {"timeline": ["2000-01-01: overdue event"]},
    )
    monkeypatch.setattr(deadline_reminder_service, "_fetch_active_cases", lambda: [case_row])
    monkeypatch.setattr(deadline_reminder_service, "_fetch_timeline_events", lambda case_id: [])

    sent_messages = []
    monkeypatch.setattr(
        deadline_reminder_service,
        "create_notification",
        lambda user_id, message, notification_type: sent_messages.append((user_id, message, notification_type)),
    )

    # First run: nothing recorded yet, so the overdue deadline is new.
    monkeypatch.setattr(deadline_reminder_service, "_mark_sent_if_new", lambda *a, **k: True)
    sent = deadline_reminder_service.scan_and_notify_deadlines()
    assert sent == 1
    assert sent_messages[0][0] == 5
    assert sent_messages[0][2] == "deadline_reminder"

    # Second run: already recorded, so no duplicate notification.
    sent_messages.clear()
    monkeypatch.setattr(deadline_reminder_service, "_mark_sent_if_new", lambda *a, **k: False)
    sent_again = deadline_reminder_service.scan_and_notify_deadlines()
    assert sent_again == 0
    assert sent_messages == []


def test_threshold_for_buckets_days_correctly():
    assert deadline_reminder_service._threshold_for(-1) == "overdue"
    assert deadline_reminder_service._threshold_for(0) == "1_day"
    assert deadline_reminder_service._threshold_for(2) == "3_day"
    assert deadline_reminder_service._threshold_for(5) == "7_day"
    assert deadline_reminder_service._threshold_for(30) is None


# ---------------------------------------------------------------------------
# Issue #12: Stripe payments fail safe without configured keys.
# ---------------------------------------------------------------------------


def test_create_checkout_session_disabled_without_secret_key(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)

    result = payment_service.create_checkout_session(
        user_id=1, plan="pro", success_url="https://example.com/ok", cancel_url="https://example.com/cancel"
    )

    assert result["enabled"] is False
    assert "STRIPE_SECRET_KEY" in result["reason"]


def test_create_checkout_session_disabled_without_price_id(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.delenv("STRIPE_PRICE_PRO", raising=False)

    result = payment_service.create_checkout_session(
        user_id=1, plan="pro", success_url="https://example.com/ok", cancel_url="https://example.com/cancel"
    )

    assert result["enabled"] is False
    assert "STRIPE_PRICE_PRO" in result["reason"]


def test_create_checkout_session_rejects_unknown_plan():
    result = payment_service.create_checkout_session(
        user_id=1, plan="unlimited-everything", success_url="https://x", cancel_url="https://y"
    )
    assert result["enabled"] is False


def test_create_checkout_session_calls_stripe_when_configured(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setenv("STRIPE_PRICE_PRO", "price_123")

    class _FakeSession:
        url = "https://checkout.stripe.com/fake"
        id = "cs_test_123"

    class _FakeCheckout:
        class Session:
            @staticmethod
            def create(**kwargs):
                assert kwargs["line_items"][0]["price"] == "price_123"
                return _FakeSession()

    class _FakeStripeModule:
        checkout = _FakeCheckout
        api_key = None

    monkeypatch.setattr(payment_service, "_stripe_module", lambda: _FakeStripeModule)

    result = payment_service.create_checkout_session(
        user_id=1, plan="pro", success_url="https://example.com/ok", cancel_url="https://example.com/cancel"
    )

    assert result["enabled"] is True
    assert result["checkout_url"] == "https://checkout.stripe.com/fake"


def test_handle_webhook_event_disabled_without_webhook_secret(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)

    result = payment_service.handle_webhook_event(b"{}", "sig")

    assert result["enabled"] is False
