import json
from typing import Annotated

from fastapi import APIRouter, Query
from db.database import get_db_connection
from models.case import CaseApplyRequest, CaseCreateRequest, CaseEventRequest
from services.ai_service import analyze_legal_problem, build_case_brief, LEGAL_DEFAULT_AREA
from services.matching_service import rank_lawyers, refresh_lawyer_responsiveness
from services.notification_service import create_notification

router = APIRouter(tags=["cases"])
USER_ROLE_QUERY = "SELECT COALESCE(role, 'client') FROM users WHERE id = %s"


def _is_role(user_id: int, required_role: str) -> bool:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(USER_ROLE_QUERY, (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return False
    return (row[0] or "client").strip().lower() == required_role


def _normalize_case_status(raw_status: str | None) -> str:
    status = (raw_status or "open").strip().lower()
    return status if status in ("open", "closed") else "open"


def _normalize_urgency(raw_urgency: str | None) -> str:
    urgency = (raw_urgency or "").strip().capitalize()
    return urgency if urgency in ("Low", "Medium", "High") else "Medium"


def _build_case_defaults(data: CaseCreateRequest, analysis: dict) -> dict:
    problem_text = f"{data.title}. {data.description}".strip()
    legal_area = (data.legal_area or "").strip() or str(
        analysis.get("legal_area") or LEGAL_DEFAULT_AREA
    ).strip()
    issue_type = (data.issue_type or "").strip() or str(
        analysis.get("issue_type") or "General Inquiry"
    ).strip()
    ai_summary = (data.ai_summary or "").strip() or str(
        analysis.get("summary") or data.description
    ).strip()
    city = (data.city or "").strip() or str(analysis.get("location") or "").strip()
    case_brief = data.case_brief or analysis.get("case_brief") or build_case_brief(
        problem_text,
        analysis,
        actor_key=f"user:{data.client_id}",
    )
    return {
        "problem_text": problem_text,
        "legal_area": legal_area,
        "issue_type": issue_type,
        "ai_summary": ai_summary,
        "city": city,
        "case_brief": case_brief,
        "status": _normalize_case_status(data.status),
        "urgency": _normalize_urgency(data.urgency),
    }


def _insert_case(data: CaseCreateRequest, payload: dict) -> tuple[int, str]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO cases (
            client_id, title, description, legal_area, issue_type, ai_summary, urgency, city, case_brief, status, is_public
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
        RETURNING case_id, created_at
        """,
        (
            data.client_id,
            data.title.strip(),
            data.description.strip(),
            payload["legal_area"],
            payload["issue_type"],
            payload["ai_summary"],
            payload["urgency"],
            payload["city"],
            json.dumps(payload["case_brief"]),
            payload["status"],
            bool(data.publish_publicly),
        ),
    )
    inserted = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return inserted[0], str(inserted[1])


def _case_row_to_dict(row: tuple) -> dict:
    return {
        "case_id": row[0],
        "client_id": row[1],
        "title": row[2],
        "description": row[3],
        "legal_area": row[4],
        "issue_type": row[5],
        "ai_summary": row[6],
        "urgency": row[7],
        "city": row[8],
        "case_brief": row[9] or {},
        "created_at": str(row[10]),
        "status": row[11],
        "is_public": row[12],
    }


def _fallback_recommended_case(row: tuple) -> dict:
    return {
        "case_id": row[0],
        "client_id": row[1],
        "title": row[2],
        "description": row[3],
        "legal_area": row[4],
        "issue_type": row[5],
        "ai_summary": row[6],
        "urgency": row[7],
        "city": row[8],
        "created_at": str(row[9]),
        "status": row[10],
        "match_score": 0,
        "match_reason": ["No lawyer profile data available yet for personalized scoring."],
    }


def _score_recommended_case(
    row: tuple,
    lawyer_id: int,
    lawyer_city: str,
    practice_areas: list[str],
    languages: str,
) -> dict:
    legal_area = (row[4] or "").strip().lower()
    case_city = (row[8] or "").strip().lower()
    case_query = f"{row[2]} {row[3]} {row[4]} {row[5]} {row[8]}"
    lawyer_match = rank_lawyers(
        query_text=case_query,
        legal_area=row[4],
        city=row[8],
        language=languages,
        case_id=row[0],
        limit=50,
    )
    embedding_component = 0.0
    match_reason = ["Recommended from your stated practice areas and location."]
    for item in lawyer_match:
        if item.get("id") == lawyer_id:
            embedding_component = float(item.get("score", 0.0))
            match_reason = item.get("match_reason") or match_reason
            break

    score = embedding_component
    if legal_area and any(pa in legal_area or legal_area in pa for pa in practice_areas):
        score += 2.0
    if lawyer_city and case_city and lawyer_city == case_city:
        score += 1.0

    fallback = _fallback_recommended_case(row)
    fallback["match_score"] = score
    fallback["match_reason"] = match_reason
    return fallback


@router.post("/cases/create")
async def create_case(data: CaseCreateRequest):
    if not _is_role(data.client_id, "client"):
        return {"success": False, "message": "Only client users can create cases."}

    analysis = analyze_legal_problem(f"{data.title}. {data.description}".strip(), actor_key=f"user:{data.client_id}")
    payload = _build_case_defaults(data, analysis)
    case_id, created_at = _insert_case(data, payload)

    suggestions_query = f"{data.title} {data.description} {payload['legal_area']} {payload['issue_type']}".strip()
    suggested_lawyers = rank_lawyers(
        query_text=suggestions_query,
        legal_area=payload["legal_area"],
        city=payload["city"],
        case_id=case_id,
        limit=5,
    )

    if suggested_lawyers:
        create_notification(
            user_id=data.client_id,
            message=f"New recommended lawyers are available for case #{case_id}.",
            notification_type="recommendation",
        )

    return {
        "success": True,
        "case_id": case_id,
        "created_at": created_at,
        "legal_area": payload["legal_area"],
        "issue_type": payload["issue_type"],
        "urgency": payload["urgency"],
        "location": payload["city"],
        "ai_summary": payload["ai_summary"],
        "case_brief": payload["case_brief"],
        "analysis": analysis,
        "suggested_lawyers": suggested_lawyers,
    }


@router.get("/cases/my")
async def get_my_cases(client_id: Annotated[int, Query()]):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT case_id, client_id, title, description, legal_area, issue_type, ai_summary, urgency,
             city, case_brief, created_at, status, is_public
        FROM cases
        WHERE client_id = %s
        ORDER BY created_at DESC
        """,
        (client_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [_case_row_to_dict(row) for row in rows]


@router.get("/cases/{case_id}")
async def get_case_detail(case_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT case_id, client_id, title, description, legal_area, issue_type, ai_summary, urgency,
               city, case_brief, created_at, status, is_public
        FROM cases
        WHERE case_id = %s
        """,
        (case_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return {}

    return _case_row_to_dict(row)


@router.get("/cases/client/{client_id}")
async def get_cases_by_client(client_id: int):
    return await get_my_cases(client_id=client_id)


@router.get("/cases/open")
async def get_open_cases():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT c.case_id, c.client_id, c.title, c.description, c.legal_area, c.issue_type,
               c.ai_summary, c.urgency, c.city, c.created_at, c.status
        FROM cases c
        WHERE c.status = 'open' AND c.is_public = TRUE
        ORDER BY c.created_at DESC
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "case_id": r[0],
            "client_id": r[1],
            "title": r[2],
            "description": r[3],
            "legal_area": r[4],
            "issue_type": r[5],
            "ai_summary": r[6],
            "urgency": r[7],
            "city": r[8],
            "created_at": str(r[9]),
            "status": r[10],
        }
        for r in rows
    ]


@router.get("/cases/recommended/{lawyer_id}")
async def get_recommended_cases_for_lawyer(lawyer_id: int):
    if not _is_role(lawyer_id, "lawyer"):
        return []

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT city, practice_areas, languages
        FROM lawyer_profiles
        WHERE lawyer_id = %s
        """,
        (lawyer_id,),
    )
    profile = cur.fetchone()

    cur.execute(
        """
        SELECT case_id, client_id, title, description, legal_area, issue_type, ai_summary, urgency,
               city, created_at, status
        FROM cases
        WHERE status = 'open' AND is_public = TRUE
        ORDER BY created_at DESC
        """
    )
    cases = cur.fetchall()
    cur.close()
    conn.close()

    if not profile:
        return [_fallback_recommended_case(row) for row in cases[:10]]

    lawyer_city = (profile[0] or "").strip().lower()
    practice_areas = [p.strip().lower() for p in (profile[1] or "").split(",") if p.strip()]
    languages = (profile[2] or "").strip().lower()

    scored = [
        _score_recommended_case(row, lawyer_id, lawyer_city, practice_areas, languages)
        for row in cases
    ]

    scored.sort(key=lambda item: (item["match_score"], item["created_at"]), reverse=True)
    return scored


@router.post("/cases/apply")
async def apply_to_case(data: CaseApplyRequest):
    if not _is_role(data.lawyer_id, "lawyer"):
        return {"success": False, "message": "Only lawyer users can apply to cases."}

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT status, client_id FROM cases WHERE case_id = %s", (data.case_id,))
    case_row = cur.fetchone()
    if not case_row:
        cur.close()
        conn.close()
        return {"success": False, "message": "Case not found."}

    if (case_row[0] or "").lower() != "open":
        cur.close()
        conn.close()
        return {"success": False, "message": "Case is not open for applications."}

    cur.execute(
        """
        INSERT INTO case_applications (case_id, lawyer_id, message, status)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (case_id, lawyer_id)
        DO UPDATE SET
            message = EXCLUDED.message,
            status = EXCLUDED.status,
            created_at = CURRENT_TIMESTAMP
        """,
        (data.case_id, data.lawyer_id, data.message.strip(), data.status.strip()),
    )

    conn.commit()
    cur.close()
    conn.close()
    refresh_lawyer_responsiveness(data.lawyer_id, increment_applications=True)
    create_notification(
        user_id=case_row[1],
        message=f"A lawyer applied to your case #{data.case_id}.",
        notification_type="application",
    )
    return {"success": True}


@router.get("/cases/applications/{lawyer_id}")
async def get_lawyer_applications(lawyer_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ca.id, ca.case_id, ca.lawyer_id, ca.message, ca.created_at, ca.status,
               c.title, c.legal_area, c.city, c.status
        FROM case_applications ca
        JOIN cases c ON ca.case_id = c.case_id
        WHERE ca.lawyer_id = %s
        ORDER BY ca.created_at DESC
        """,
        (lawyer_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "id": r[0],
            "case_id": r[1],
            "lawyer_id": r[2],
            "message": r[3],
            "created_at": str(r[4]),
            "application_status": r[5],
            "title": r[6],
            "legal_area": r[7],
            "city": r[8],
            "status": r[9],
        }
        for r in rows
    ]


@router.get("/cases/{case_id}/applications")
async def get_case_applications(case_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ca.id, ca.case_id, ca.lawyer_id, u.name, ca.message, ca.created_at, ca.status
        FROM case_applications ca
        JOIN users u ON u.id = ca.lawyer_id
        WHERE ca.case_id = %s
        ORDER BY ca.created_at DESC
        """,
        (case_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "id": row[0],
            "case_id": row[1],
            "lawyer_id": row[2],
            "lawyer_name": row[3],
            "message": row[4],
            "created_at": str(row[5]),
            "status": row[6],
        }
        for row in rows
    ]


@router.get("/cases/{case_id}/events")
async def get_case_events(case_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, description, event_date, created_at
        FROM case_events
        WHERE case_id = %s
        ORDER BY event_date ASC, created_at ASC
        """,
        (case_id,),
    )
    rows = cur.fetchall()

    cur.execute(
        """
        SELECT title, description, case_brief
        FROM cases
        WHERE case_id = %s
        """,
        (case_id,),
    )
    case_row = cur.fetchone()
    cur.close()
    conn.close()

    items = [
        {
            "id": row[0],
            "description": row[1],
            "event_date": str(row[2]),
            "created_at": str(row[3]),
        }
        for row in rows
    ]

    timeline_summary = ""
    if case_row:
        bullet_points = [f"{item['event_date']}: {item['description']}" for item in items]
        brief = (case_row[2] or {}) if len(case_row) > 2 else {}
        timeline_summary = " ".join(bullet_points) or "No timeline events added yet."
        if isinstance(brief, dict) and brief.get("timeline"):
            timeline_summary = " ".join([str(entry) for entry in brief.get("timeline", [])])

    return {"items": items, "timeline_summary": timeline_summary}


@router.post("/cases/{case_id}/events")
async def add_case_event(case_id: int, data: CaseEventRequest):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO case_events (case_id, description, event_date)
        VALUES (%s, %s, %s)
        RETURNING id, created_at
        """,
        (case_id, data.description.strip(), data.event_date),
    )
    inserted = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return {"success": True, "id": inserted[0], "created_at": str(inserted[1])}
