from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth_utils import create_access_token
from routers import cases as cases_module
from routers import lawyers as lawyers_module
from routers import realtime as realtime_module
from routers.cases import router as cases_router
from routers.lawyers import router as lawyers_router


class ScriptedCursor:
    """A fake DB cursor that returns canned fetchone/fetchall results in order."""

    def __init__(self, fetchone_results=None, fetchall_results=None):
        self._fetchone_iter = iter(fetchone_results or [])
        self._fetchall_iter = iter(fetchall_results or [])
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchone(self):
        return next(self._fetchone_iter, None)

    def fetchall(self):
        return next(self._fetchall_iter, [])

    def close(self):
        pass


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
# Issue #29: /cases/open and /cases/recommended must drop a case once it has
# an accepted application, not just filter on status = 'open'.
# ---------------------------------------------------------------------------


def test_open_cases_query_excludes_cases_with_an_accepted_application(monkeypatch):
    cursor = ScriptedCursor(fetchall_results=[[]])
    monkeypatch.setattr(cases_module, "get_db_connection", lambda: ScriptedConnection(cursor))

    app = FastAPI()
    app.include_router(cases_router)
    client = TestClient(app)

    response = client.get("/cases/open")

    assert response.status_code == 200
    query, _ = cursor.executed[0]
    assert "case_applications" in query
    assert "status = 'accepted'" in query
    assert "NOT EXISTS" in query


def test_recommended_cases_query_excludes_cases_with_an_accepted_application(monkeypatch):
    cursor = ScriptedCursor(
        fetchone_results=[
            ("lawyer",),  # _is_role(lawyer_id, "lawyer")
            None,  # lawyer_profiles row (missing profile -> fallback path)
        ],
        fetchall_results=[[]],
    )
    monkeypatch.setattr(cases_module, "get_db_connection", lambda: ScriptedConnection(cursor))

    app = FastAPI()
    app.include_router(cases_router)
    client = TestClient(app)

    token = create_access_token(user_id=42, role="lawyer", email="lawyer42@example.com")
    response = client.get(
        "/cases/recommended/42",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    # execute() calls: _is_role's query, the lawyer_profiles lookup, then
    # the cases listing query.
    query, _ = cursor.executed[2]
    assert "case_applications" in query
    assert "status = 'accepted'" in query
    assert "NOT EXISTS" in query


# ---------------------------------------------------------------------------
# Issue #30: booking a consultation slot must require an *accepted*
# application, not merely any application row for (case_id, lawyer_id).
# ---------------------------------------------------------------------------


def _lawyers_app() -> TestClient:
    app = FastAPI()
    app.include_router(lawyers_router)
    return TestClient(app)


def test_book_availability_slot_rejects_pending_application(monkeypatch):
    cursor = ScriptedCursor(
        fetchone_results=[
            (5,),  # case client_id lookup -> client_id == caller, participant
            (42, False),  # slot: lawyer_id, is_booked
            None,  # no *accepted* application row for (case_id, lawyer_id)
        ],
    )

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
    assert "not been accepted" in body["message"]
    assert conn.rolled_back == 1
    assert conn.committed == 0

    # Confirm the guard query actually filters on accepted status.
    accepted_check_query = next(
        q for q, _ in cursor.executed if "FROM case_applications" in q
    )
    assert "status = 'accepted'" in accepted_check_query


def test_book_availability_slot_allows_accepted_application(monkeypatch):
    cursor = ScriptedCursor(
        fetchone_results=[
            (5,),  # case client_id lookup
            (42, False),  # slot: lawyer_id, is_booked
            (1,),  # accepted application exists
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
    assert conn.committed == 1


# ---------------------------------------------------------------------------
# Issue #31: _case_membership (WebSocket connection gate) must match
# _case_participants (message routing / REST), admitting any applicant
# lawyer regardless of application status.
# ---------------------------------------------------------------------------


def test_case_membership_admits_pending_applicant_lawyer(monkeypatch):
    monkeypatch.setattr(
        realtime_module, "_case_participants", lambda case_id: {99, 7, 8}
    )

    # Lawyer 7 has only a pending/rejected application (not 'accepted'), but
    # must still be treated as a member, same as REST chat + message routing.
    assert realtime_module._case_membership(case_id=5, user_id=7) is True
    assert realtime_module._case_membership(case_id=5, user_id=99) is True
    assert realtime_module._case_membership(case_id=5, user_id=404) is False


def test_case_membership_returns_false_for_missing_case(monkeypatch):
    monkeypatch.setattr(realtime_module, "_case_participants", lambda case_id: None)

    assert realtime_module._case_membership(case_id=999, user_id=1) is False


def test_case_membership_matches_case_participants_on_real_query(monkeypatch):
    """End-to-end (fake DB) check that the connection gate and message
    routing agree for a lawyer whose application is merely 'submitted'."""
    cursor = ScriptedCursor(
        fetchone_results=[(99,)],  # client_id for _case_participants
        fetchall_results=[[(7,)]],  # applicant lawyer_ids, status irrelevant
    )
    monkeypatch.setattr(realtime_module, "get_db_connection", lambda: ScriptedConnection(cursor))

    assert realtime_module._case_membership(case_id=5, user_id=7) is True
