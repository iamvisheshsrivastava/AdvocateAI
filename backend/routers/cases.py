from fastapi import APIRouter, Query
from db.database import get_db_connection
from models.case import CaseApplyRequest, CaseCreateRequest
from services.ai_service import analyze_legal_problem, LEGAL_DEFAULT_AREA
from services.matching_service import rank_lawyers

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


@router.post("/cases/create")
async def create_case(data: CaseCreateRequest):
    if not _is_role(data.client_id, "client"):
        return {"success": False, "message": "Only client users can create cases."}

    status = (data.status or "open").strip().lower()
    if status not in ("open", "closed"):
        status = "open"

    urgency = (data.urgency or "").strip().capitalize()
    if urgency not in ("Low", "Medium", "High"):
        urgency = "Medium"

    analysis = analyze_legal_problem(f"{data.title}. {data.description}".strip())

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

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO cases (
            client_id, title, description, legal_area, issue_type, ai_summary, urgency, city, status, is_public
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING case_id, created_at
        """,
        (
            data.client_id,
            data.title.strip(),
            data.description.strip(),
            legal_area,
            issue_type,
            ai_summary,
            urgency,
            city,
            status,
            bool(data.publish_publicly),
        ),
    )
    inserted = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    suggestions_query = f"{data.title} {data.description} {legal_area} {issue_type}".strip()
    suggested_lawyers = rank_lawyers(
        query_text=suggestions_query,
        legal_area=legal_area,
        city=city,
        limit=5,
    )

    return {
        "success": True,
        "case_id": inserted[0],
        "created_at": str(inserted[1]),
        "legal_area": legal_area,
        "issue_type": issue_type,
        "urgency": urgency,
        "location": city,
        "ai_summary": ai_summary,
        "suggested_lawyers": suggested_lawyers,
    }


@router.get("/cases/my")
async def get_my_cases(client_id: int = Query(...)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT case_id, client_id, title, description, legal_area, issue_type, ai_summary, urgency,
               city, created_at, status, is_public
        FROM cases
        WHERE client_id = %s
        ORDER BY created_at DESC
        """,
        (client_id,),
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
            "is_public": r[11],
        }
        for r in rows
    ]


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
                "match_score": 0,
            }
            for r in cases[:10]
        ]

    lawyer_city = (profile[0] or "").strip().lower()
    practice_areas = [p.strip().lower() for p in (profile[1] or "").split(",") if p.strip()]
    languages = (profile[2] or "").strip().lower()

    scored = []
    for r in cases:
        legal_area = (r[4] or "").strip().lower()
        case_city = (r[8] or "").strip().lower()
        case_query = f"{r[2]} {r[3]} {r[4]} {r[5]} {r[8]}"

        lawyer_match = rank_lawyers(
            query_text=case_query,
            legal_area=r[4],
            city=r[8],
            language=languages,
            limit=50,
        )
        embedding_component = 0.0
        for item in lawyer_match:
            if item.get("id") == lawyer_id:
                embedding_component = float(item.get("score", 0.0))
                break

        score = 0.0
        if legal_area and any(pa in legal_area or legal_area in pa for pa in practice_areas):
            score += 2.0
        if lawyer_city and case_city and lawyer_city == case_city:
            score += 1.0
        score += embedding_component

        scored.append(
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
                "match_score": score,
            }
        )

    scored.sort(key=lambda item: (item["match_score"], item["created_at"]), reverse=True)
    return scored


@router.post("/cases/apply")
async def apply_to_case(data: CaseApplyRequest):
    if not _is_role(data.lawyer_id, "lawyer"):
        return {"success": False, "message": "Only lawyer users can apply to cases."}

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT status FROM cases WHERE case_id = %s", (data.case_id,))
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
