from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from auth_utils import get_current_user
from db.database import get_db_connection
from models.lawyer import LawyerProfileRequest, WatchlistRequest
from services.ml_matching_service import recommend_lawyers_for_case_ml
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["lawyers"])
USER_ROLE_QUERY = "SELECT COALESCE(role, 'client') FROM users WHERE id = %s"


def _require_self(current_user: dict, user_id: int, message: str) -> None:
    """Raise 403 unless the authenticated caller's JWT subject matches user_id."""
    if str(current_user.get("sub")) != str(user_id):
        raise HTTPException(status_code=403, detail=message)


def _safe_list_to_text(value: list[str] | str) -> str:
    if isinstance(value, list):
        return ", ".join([v.strip() for v in value if v and v.strip()])
    return value.strip()


@router.post("/lawyer/profile")
async def upsert_lawyer_profile(data: LawyerProfileRequest, current_user: dict = Depends(get_current_user)):
    _require_self(current_user, data.lawyer_id, "You can only edit your own lawyer profile.")
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(USER_ROLE_QUERY, (data.lawyer_id,))
    user = cur.fetchone()
    if not user:
        cur.close()
        conn.close()
        return {"success": False, "message": "Lawyer user not found."}

    if (user[0] or "client").strip().lower() != "lawyer":
        cur.close()
        conn.close()
        return {"success": False, "message": "Only lawyer users can create a lawyer profile."}

    practice_areas_text = _safe_list_to_text(data.practice_areas)
    languages_text = _safe_list_to_text(data.languages)

    cur.execute(
        """
        INSERT INTO lawyer_profiles (
            lawyer_id, name, city, practice_areas, languages, experience_years, rating, bio, availability_status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (lawyer_id)
        DO UPDATE SET
            name = EXCLUDED.name,
            city = EXCLUDED.city,
            practice_areas = EXCLUDED.practice_areas,
            languages = EXCLUDED.languages,
            experience_years = EXCLUDED.experience_years,
            rating = EXCLUDED.rating,
            bio = EXCLUDED.bio,
            availability_status = EXCLUDED.availability_status,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            data.lawyer_id,
            data.name.strip(),
            data.city.strip(),
            practice_areas_text,
            languages_text,
            max(0, data.experience_years),
            max(0, float(data.rating)),
            data.bio.strip(),
            data.availability_status.strip() or "available",
        ),
    )

    conn.commit()
    cur.close()
    conn.close()
    return {"success": True}


@router.get("/lawyer/profile/{lawyer_id}")
async def get_lawyer_profile(lawyer_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT lawyer_id, name, city, practice_areas, languages, experience_years, rating, bio,
               availability_status, response_time_hours, applications_sent, cases_accepted,
               responsiveness_score
        FROM lawyer_profiles
        WHERE lawyer_id = %s
        """,
        (lawyer_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Lawyer profile not found.")

    return {
        "lawyer_id": row[0],
        "name": row[1],
        "city": row[2],
        "practice_areas": row[3],
        "languages": row[4],
        "experience_years": row[5],
        "rating": row[6],
        "bio": row[7],
        "availability_status": row[8],
        "response_time_hours": row[9],
        "applications_sent": row[10],
        "cases_accepted": row[11],
        "responsiveness_score": row[12],
    }


@router.get("/lawyers/recommended/{case_id}")
async def get_recommended_lawyers(case_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT client_id FROM cases WHERE case_id = %s", (case_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Case not found.")
    _require_self(current_user, row[0], "Only the case owner can view lawyer recommendations for this case.")

    response = recommend_lawyers_for_case_ml(case_id, limit=5)
    return response.get("items", [])


@router.get("/watchlist/{user_id}")
async def get_watchlist(user_id: int, current_user: dict = Depends(get_current_user)):
    _require_self(current_user, user_id, "You can only view your own watchlist.")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.id, p.name, p.city, p.category, p.rating, p.review_count
        FROM watchlist w
        JOIN professionals p ON w.professional_id = p.id
        WHERE w.user_id = %s
        ORDER BY p.rating DESC
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "id": r[0],
            "name": r[1],
            "city": r[2],
            "category": r[3],
            "rating": r[4],
            "reviews": r[5],
        }
        for r in rows
    ]


@router.get("/professionals/{user_id}")
async def get_professionals(
    user_id: int,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    current_user: dict = Depends(get_current_user),
):
    _require_self(current_user, user_id, "You can only browse professionals as yourself.")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, name, city, rating, review_count
        FROM professionals
        WHERE id NOT IN (
            SELECT professional_id
            FROM watchlist
            WHERE user_id = %s
        )
        ORDER BY rating DESC
        LIMIT %s OFFSET %s
        """,
        (user_id, limit, offset),
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "id": r[0],
            "name": r[1],
            "city": r[2],
            "rating": r[3],
            "reviews": r[4],
        }
        for r in rows
    ]


@router.post("/watchlist/add")
async def add_to_watchlist(data: WatchlistRequest, current_user: dict = Depends(get_current_user)):
    _require_self(current_user, data.user_id, "You can only modify your own watchlist.")
    conn = get_db_connection()
    cur = conn.cursor()

    for pid in data.professional_ids:
        cur.execute(
            """
            INSERT INTO watchlist (user_id, professional_id)
            VALUES (%s, %s)
            ON CONFLICT (user_id, professional_id) DO NOTHING
            """,
            (data.user_id, pid),
        )

    conn.commit()
    cur.close()
    conn.close()

    return {"success": True}
