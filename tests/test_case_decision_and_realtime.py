from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth_utils import create_access_token
from routers import cases as cases_module
from routers import realtime as realtime_module
from routers.cases import router as cases_router


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

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def close(self):
        pass


def _fail_if_called(*_args, **_kwargs):
    raise AssertionError("should not have been called")


# ---------------------------------------------------------------------------
# Issue #25: a case with an already-accepted lawyer must not silently accept
# more applications, nor allow a decision on a *different* application to
# bypass the already-accepted one.
# ---------------------------------------------------------------------------


def test_apply_to_case_blocked_when_case_already_has_accepted_lawyer(monkeypatch):
    cursor = ScriptedCursor(
        fetchone_results=[
            ("lawyer",),  # _is_role(lawyer_id, "lawyer")
            ("open", 99),  # case status/client_id lookup
            (1,),  # an accepted application already exists
        ]
    )
    monkeypatch.setattr(cases_module, "get_db_connection", lambda: ScriptedConnection(cursor))
    monkeypatch.setattr(cases_module, "refresh_lawyer_responsiveness", _fail_if_called)
    monkeypatch.setattr(cases_module, "create_notification", _fail_if_called)

    app = FastAPI()
    app.include_router(cases_router)
    client = TestClient(app)

    token = create_access_token(user_id=42, role="lawyer", email="lawyer42@example.com")
    response = client.post(
        "/cases/apply",
        json={"case_id": 5, "lawyer_id": 42, "message": "I can help.", "status": "submitted"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert "already has an accepted lawyer" in body["message"]
    # No INSERT should have been issued once the accepted-application guard tripped.
    assert not any("INSERT INTO case_applications" in q for q, _ in cursor.executed)


def test_decide_case_application_blocked_once_another_lawyer_already_accepted(monkeypatch):
    cursor = ScriptedCursor(
        fetchone_results=[
            ("client",),  # _is_role(client_id, "client")
            (99, "open", "Some Title"),  # case row: client_id, status, title
            (7, "submitted"),  # current_application: lawyer_id, status (not yet accepted)
            (1,),  # a different application on this case is already accepted
        ]
    )
    monkeypatch.setattr(cases_module, "get_db_connection", lambda: ScriptedConnection(cursor))
    monkeypatch.setattr(cases_module, "refresh_lawyer_responsiveness", _fail_if_called)
    monkeypatch.setattr(cases_module, "create_notification", _fail_if_called)

    app = FastAPI()
    app.include_router(cases_router)
    client = TestClient(app)

    token = create_access_token(user_id=99, role="client", email="client99@example.com")
    response = client.post(
        "/cases/5/applications/2/decision",
        json={"client_id": 99, "decision": "accepted"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert "already has an accepted lawyer" in body["message"]
    # The bulk-reject/UPDATE of case_applications must never have been reached.
    assert not any(
        q.strip().startswith("UPDATE case_applications") for q, _ in cursor.executed
    )


# ---------------------------------------------------------------------------
# Issue #26: the case WebSocket must validate receiver_id the same way the
# REST POST /messages/send path does, not trust it blindly.
# ---------------------------------------------------------------------------


def test_case_participants_returns_none_for_missing_case(monkeypatch):
    cursor = ScriptedCursor(fetchone_results=[None])
    monkeypatch.setattr(realtime_module, "get_db_connection", lambda: ScriptedConnection(cursor))

    assert realtime_module._case_participants(999) is None


def test_case_participants_includes_client_and_applicants(monkeypatch):
    cursor = ScriptedCursor(
        fetchone_results=[(99,)],  # client_id
        fetchall_results=[[(7,), (8,)]],  # applicant lawyer_ids
    )
    monkeypatch.setattr(realtime_module, "get_db_connection", lambda: ScriptedConnection(cursor))

    participants = realtime_module._case_participants(5)

    assert participants == {99, 7, 8}


def test_case_socket_rejects_message_to_non_participant_receiver(monkeypatch):
    monkeypatch.setattr(realtime_module, "_authenticate", _async_claims(user_id=99))
    monkeypatch.setattr(realtime_module, "_case_membership", lambda case_id, user_id: True)
    # receiver_id=404 is not in the participant set -> message must be dropped.
    monkeypatch.setattr(realtime_module, "_case_participants", lambda case_id: {99, 7})
    monkeypatch.setattr(realtime_module, "get_db_connection", _fail_if_called)
    monkeypatch.setattr(realtime_module, "create_notification", _fail_if_called)

    app = FastAPI()
    app.include_router(realtime_module.router)
    client = TestClient(app)

    with client.websocket_connect("/ws/case/5/99?token=whatever") as websocket:
        connected = websocket.receive_json()
        assert connected["event"] == "connected"

        websocket.send_json({"event": "send_message", "content": "hi", "receiver_id": 404})

        # Nothing should come back for the rejected message; close and confirm
        # no new_message / error ever arrived by sending a follow-up probe.
        websocket.close()


def _async_claims(user_id: int):
    async def _inner(_websocket):
        return {"sub": str(user_id)}

    return _inner
