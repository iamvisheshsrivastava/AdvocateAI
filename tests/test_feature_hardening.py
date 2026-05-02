from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from errors import AppError
from app import app as backend_app
from routers.ml import router as ml_router
from routers.notifications import router as notifications_router
from services import legal_action_service
from services import matching_service


def _raise_runtime_error(*_args, **_kwargs):
    raise RuntimeError("boom")


def test_legal_action_guide_falls_back_for_unknown_issue(monkeypatch):
    monkeypatch.setattr(legal_action_service, "LEGAL_ACTIONS", {})
    monkeypatch.setattr(legal_action_service.cache_service, "get", lambda _key: None)
    monkeypatch.setattr(legal_action_service.cache_service, "set", lambda *args, **kwargs: None)
    monkeypatch.setattr(legal_action_service, "GEMINI_API_KEY", None)

    guide = legal_action_service.build_legal_action_guide("something unusual happened")

    assert guide["issue_type"] == "unknown"
    assert guide["actions"]
    assert guide["disclaimer"]


def test_responsiveness_score_ranges_are_bounded():
    score = matching_service._compute_responsiveness_score(4, 8, 4)

    assert 0.0 <= score <= 1.0


def test_match_reason_includes_contextual_clues():
    reasons = matching_service._build_match_reason(
        legal_area="Tenant Dispute",
        city="Austin",
        professional_city="Austin",
        category="Tenant Dispute",
        languages="English, Spanish",
        availability_status="available",
        embedding_score=0.7,
        responsiveness_score=0.8,
    )

    assert any("Specializes" in reason for reason in reasons)
    assert any("Located" in reason for reason in reasons)


def test_notifications_router_handles_service_failures(monkeypatch):
    monkeypatch.setattr("routers.notifications.get_notifications", _raise_runtime_error)
    monkeypatch.setattr("routers.notifications.mark_notifications_read", _raise_runtime_error)

    app = FastAPI()
    app.include_router(notifications_router)
    client = TestClient(app)

    response = client.get("/notifications", params={"user_id": 1})
    assert response.status_code == 200
    assert response.json() == {"items": [], "unread_count": 0}

    response = client.post("/notifications/read", json={"user_id": 1, "notification_ids": [1, 2]})
    assert response.status_code == 200
    assert response.json() == {"success": False}


def test_ml_router_training_failure_returns_error(monkeypatch):
    def _raise_train_error(**_kwargs):
        raise RuntimeError("train failed")

    monkeypatch.setattr("routers.ml.train_lawyer_match_model", _raise_train_error)
    monkeypatch.setattr("routers.ml.get_model_status", lambda: {"ready": False})
    monkeypatch.setattr("routers.ml.recommend_lawyers_for_case_ml", lambda case_id, limit=5: {"case_id": case_id, "items": []})

    app = FastAPI()
    app.include_router(ml_router)
    client = TestClient(app)

    response = client.post("/ml/lawyer-matching/train")
    assert response.status_code == 200
    assert response.json()["success"] is False
    assert "train failed" in response.json()["error"]


def test_app_error_serializes_cleanly():
    app = FastAPI()

    @app.get("/boom")
    def boom() -> None:
        raise AppError("bad request", status_code=409, details={"field": "value"})

    app.add_exception_handler(AppError, backend_app.exception_handlers[AppError])
    client = TestClient(app)

    response = client.get("/boom")
    assert response.status_code == 409
    assert response.json()["detail"] == "bad request"
    assert response.json()["details"] == {"field": "value"}
