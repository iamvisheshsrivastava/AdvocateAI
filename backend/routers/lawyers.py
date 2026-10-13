from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from auth_utils import get_current_user
from db.database import get_db_connection
from models.lawyer import AvailabilitySlotRequest, BookingRequest, LawyerProfileRequest, WatchlistRequest
from services.ml_matching_service import recommend_lawyers_for_case_ml
from services.notification_service import create_notification
from services.realtime_service import publish_case_message
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


def _is_case_participant_for_booking(case_id: int, user_id: int) -> tuple[bool, int | None]:
    """Returns (is_participant, client_id) for the given case/user.

    A participant is the case's client, or a lawyer who has an application
    (any status) recorded against the case -- mirrors the ownership checks
    already used in routers/cases.py.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT client_id FROM cases WHERE case_id = %s", (case_id,))
    case_row = cur.fetchone()
    if not case_row:
        cur.close()
        conn.close()
        return False, None

    client_id = int(case_row[0])
    if user_id == client_id:
        cur.close()
        conn.close()
        return True, client_id

    cur.execute(
        "SELECT 1 FROM case_applications WHERE case_id = %s AND lawyer_id = %s",
        (case_id, user_id),
    )
    is_applicant_lawyer = cur.fetchone() is not None
    cur.close()
    conn.close()
    return is_applicant_lawyer, client_id


@router.post("/lawyer/availability/slots")
async def create_availability_slots(
    data: AvailabilitySlotRequest, current_user: dict = Depends(get_current_user)
):
    _require_self(current_user, data.lawyer_id, "You can only publish your own availability.")

    if data.end_time <= data.start_time:
        return {"success": False, "message": "end_time must be after start_time."}

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(USER_ROLE_QUERY, (data.lawyer_id,))
    user = cur.fetchone()
    if not user or (user[0] or "client").strip().lower() != "lawyer":
        cur.close()
        conn.close()
        return {"success": False, "message": "Only lawyer users can publish availability slots."}

    cur.execute(
        """
        INSERT INTO lawyer_availability_slots (lawyer_id, start_time, end_time)
        VALUES (%s, %s, %s)
        RETURNING id, start_time, end_time, is_booked
        """,
        (data.lawyer_id, data.start_time, data.end_time),
    )
    inserted = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return {
        "success": True,
        "slot": {
            "id": inserted[0],
            "lawyer_id": data.lawyer_id,
            "start_time": str(inserted[1]),
            "end_time": str(inserted[2]),
            "is_booked": inserted[3],
        },
    }


@router.get("/lawyer/availability/{lawyer_id}")
async def get_lawyer_availability(lawyer_id: int):
    """Public: open (unbooked, future) slots for a lawyer."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, lawyer_id, start_time, end_time, is_booked
        FROM lawyer_availability_slots
        WHERE lawyer_id = %s AND is_booked = FALSE AND start_time > CURRENT_TIMESTAMP
        ORDER BY start_time ASC
        """,
        (lawyer_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "id": r[0],
            "lawyer_id": r[1],
            "start_time": str(r[2]),
            "end_time": str(r[3]),
            "is_booked": r[4],
        }
        for r in rows
    ]


@router.post("/lawyer/availability/book")
async def book_availability_slot(data: BookingRequest, current_user: dict = Depends(get_current_user)):
    _require_self(current_user, data.client_id, "You can only book consultations as yourself.")

    is_participant, case_client_id = _is_case_participant_for_booking(data.case_id, data.client_id)
    if case_client_id is None:
        return {"success": False, "message": "Case not found."}
    if not is_participant or data.client_id != case_client_id:
        raise HTTPException(
            status_code=403,
            detail="You can only book a consultation for a case you own.",
        )

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Lock the slot row so two clients can't both book the same opening.
        cur.execute(
            """
            SELECT lawyer_id, is_booked
            FROM lawyer_availability_slots
            WHERE id = %s
            FOR UPDATE
            """,
            (data.slot_id,),
        )
        slot_row = cur.fetchone()
        if not slot_row:
            conn.rollback()
            return {"success": False, "message": "Availability slot not found."}

        lawyer_id, is_booked = int(slot_row[0]), bool(slot_row[1])
        if is_booked:
            conn.rollback()
            return {"success": False, "message": "This slot has already been booked."}

        # The lawyer who owns the slot must have an *accepted* application for
        # this case -- a rejected or still-pending applicant must not be
        # bookable (see issue #30).
        cur.execute(
            "SELECT 1 FROM case_applications WHERE case_id = %s AND lawyer_id = %s AND status = 'accepted'",
            (data.case_id, lawyer_id),
        )
        if cur.fetchone() is None:
            conn.rollback()
            return {
                "success": False,
                "message": "This lawyer has not been accepted for the case you specified.",
            }

        cur.execute(
            """
            UPDATE lawyer_availability_slots
            SET is_booked = TRUE, case_id = %s, client_id = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, start_time, end_time
            """,
            (data.case_id, data.client_id, data.slot_id),
        )
        updated = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    start_time, end_time = str(updated[1]), str(updated[2])
    message = f"Consultation booked for case #{data.case_id}: {start_time} - {end_time}."
    create_notification(user_id=lawyer_id, message=message, notification_type="booking")
    create_notification(user_id=data.client_id, message=message, notification_type="booking")
    publish_case_message(
        data.case_id,
        {
            "event": "system_message",
            "case_id": data.case_id,
            "content": f"A consultation was booked: {start_time} - {end_time}.",
        },
    )

    return {
        "success": True,
        "slot_id": updated[0],
        "case_id": data.case_id,
        "lawyer_id": lawyer_id,
        "client_id": data.client_id,
        "start_time": start_time,
        "end_time": end_time,
    }
