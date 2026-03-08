import json
import numpy as np
from db.database import get_db_connection
from services.ai_service import embed_model
from services.cache_service import cache_service


def _normalized_text(value: str | None) -> str:
    return (value or "").strip().lower()


def _compute_responsiveness_score(
    response_time_hours: float | None,
    applications_sent: int | None,
    cases_accepted: int | None,
) -> float:
    response_time = max(0.0, float(response_time_hours or 0.0))
    applications = max(0, int(applications_sent or 0))
    accepted = max(0, int(cases_accepted or 0))

    speed_score = max(0.0, 1.0 - min(response_time, 72.0) / 72.0)
    activity_score = min(applications / 20.0, 1.0)
    acceptance_ratio = min(accepted / max(applications, 1), 1.0)
    return round((speed_score * 0.45) + (activity_score * 0.2) + (acceptance_ratio * 0.35), 4)


def refresh_lawyer_responsiveness(
    lawyer_id: int,
    increment_applications: bool = False,
    increment_cases_accepted: bool = False,
    response_time_hours: float | None = None,
):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT response_time_hours, applications_sent, cases_accepted
        FROM lawyer_profiles
        WHERE lawyer_id = %s
        """,
        (lawyer_id,),
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return

    current_response_time = float(row[0] or 0.0)
    applications_sent = int(row[1] or 0)
    cases_accepted = int(row[2] or 0)

    if increment_applications:
        applications_sent += 1
    if increment_cases_accepted:
        cases_accepted += 1
    if response_time_hours is not None:
        if current_response_time > 0:
            current_response_time = round((current_response_time + response_time_hours) / 2.0, 4)
        else:
            current_response_time = round(response_time_hours, 4)

    responsiveness_score = _compute_responsiveness_score(
        current_response_time,
        applications_sent,
        cases_accepted,
    )

    cur.execute(
        """
        UPDATE lawyer_profiles
        SET response_time_hours = %s,
            applications_sent = %s,
            cases_accepted = %s,
            responsiveness_score = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE lawyer_id = %s
        """,
        (
            current_response_time,
            applications_sent,
            cases_accepted,
            responsiveness_score,
            lawyer_id,
        ),
    )
    conn.commit()
    cur.close()
    conn.close()


def _build_match_reason(
    legal_area: str | None,
    city: str | None,
    professional_city: str | None,
    category: str | None,
    languages: str | None,
    availability_status: str | None,
    embedding_score: float,
    responsiveness_score: float,
) -> list[str]:
    reasons: list[str] = []
    norm_legal_area = _normalized_text(legal_area)
    norm_category = _normalized_text(category)
    norm_city = _normalized_text(city)
    norm_professional_city = _normalized_text(professional_city)

    if norm_legal_area and norm_category and (
        norm_legal_area in norm_category or norm_category in norm_legal_area
    ):
        reasons.append(f"Specializes in {category}.")
    if norm_city and norm_professional_city and norm_city == norm_professional_city:
        reasons.append(f"Located in {professional_city}.")
    if embedding_score >= 0.55:
        reasons.append("Handled similar disputes based on semantic similarity.")
    if languages:
        reasons.append(f"Can communicate in {languages}.")
    if availability_status and availability_status != "available":
        reasons.append(f"Current availability status: {availability_status}.")
    if responsiveness_score >= 0.65:
        reasons.append("Shows strong responsiveness based on platform activity.")
    return reasons[:4]


def _ranking_cache_key(
    query_text: str,
    legal_area: str | None,
    city: str | None,
    language: str | None,
    case_id: int | None,
) -> str:
    if case_id is not None:
        return f"lawyer_match:{case_id}"
    fingerprint = "|".join([query_text, legal_area or "", city or "", language or ""])
    return f"lawyer_match:{cache_service.make_hash(fingerprint)}"


def _fetch_rankable_lawyers() -> list[tuple]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.id, p.name, p.city, p.category, p.rating, p.review_count, p.embedding,
             lp.languages, lp.availability_status, lp.response_time_hours,
             lp.applications_sent, lp.cases_accepted, lp.responsiveness_score
        FROM professionals p
        LEFT JOIN lawyer_profiles lp ON lp.lawyer_id = p.id
         WHERE p.embedding IS NOT NULL
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def _embedding_score(query_embedding: list[float], embedding_json: str) -> float | None:
    try:
        profile_embedding = np.array(json.loads(embedding_json))
        return float(np.dot(query_embedding, profile_embedding))
    except Exception:
        return None


def _scored_lawyer(
    row: tuple,
    query_embedding: list[float],
    legal_area: str | None,
    city: str | None,
    language: str | None,
) -> dict | None:
    (
        pid,
        name,
        professional_city,
        category,
        rating,
        reviews,
        embedding_json,
        languages,
        availability_status,
        response_time_hours,
        applications_sent,
        cases_accepted,
        stored_responsiveness_score,
    ) = row

    embedding_score = _embedding_score(query_embedding, embedding_json)
    if embedding_score is None:
        return None
    if _normalized_text(availability_status) == "not accepting cases":
        return None

    score = embedding_score
    norm_legal_area = _normalized_text(legal_area)
    norm_city = _normalized_text(city)
    norm_lang = _normalized_text(language)
    norm_category = _normalized_text(category)
    norm_prof_city = _normalized_text(professional_city)
    norm_languages = _normalized_text(languages)

    if norm_legal_area and norm_category and (
        norm_legal_area in norm_category or norm_category in norm_legal_area
    ):
        score += 0.30
    if norm_city and norm_prof_city and norm_city == norm_prof_city:
        score += 0.20
    if norm_lang and norm_languages and norm_lang in norm_languages:
        score += 0.15

    rating_boost = max(0.0, float(rating or 0.0)) / 10.0
    responsiveness_score = float(
        stored_responsiveness_score
        or _compute_responsiveness_score(response_time_hours, applications_sent, cases_accepted)
    )
    score += rating_boost + (responsiveness_score * 0.25)

    return {
        "id": pid,
        "lawyer_id": pid,
        "name": name,
        "city": professional_city,
        "category": category,
        "rating": rating,
        "reviews": reviews,
        "score": score,
        "match_score": score,
        "embedding_score": embedding_score,
        "match_reason": _build_match_reason(
            legal_area=legal_area,
            city=city,
            professional_city=professional_city,
            category=category,
            languages=languages,
            availability_status=availability_status,
            embedding_score=embedding_score,
            responsiveness_score=responsiveness_score,
        ),
        "availability_status": availability_status or "available",
        "responsiveness_score": responsiveness_score,
    }


def rank_lawyers(
    query_text: str,
    legal_area: str | None = None,
    city: str | None = None,
    language: str | None = None,
    case_id: int | None = None,
    limit: int = 5,
):
    if not query_text.strip():
        return []

    cache_key = _ranking_cache_key(query_text, legal_area, city, language, case_id)
    cached = cache_service.get(cache_key)
    if cached:
        return cached[:limit]

    query_embedding = embed_model.encode(query_text).tolist()
    ranked = []
    for row in _fetch_rankable_lawyers():
        scored = _scored_lawyer(row, query_embedding, legal_area, city, language)
        if scored is not None:
            ranked.append(scored)

    ranked.sort(key=lambda item: item["score"], reverse=True)
    result = ranked[:limit]
    cache_service.set(cache_key, result, ttl_seconds=900)
    return result


def recommend_lawyers_for_case(case_id: int, limit: int = 5):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT title, description, legal_area, city
        FROM cases
        WHERE case_id = %s
        """,
        (case_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return []

    title, description, legal_area, city = row
    case_query = f"{title or ''} {description or ''} {legal_area or ''} {city or ''}".strip()
    return rank_lawyers(
        query_text=case_query,
        legal_area=legal_area,
        city=city,
        case_id=case_id,
        limit=limit,
    )
