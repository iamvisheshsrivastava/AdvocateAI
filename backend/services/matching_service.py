import json
import numpy as np
from db.database import get_db_connection
from services.ai_service import embed_model


def _normalized_text(value: str | None) -> str:
    return (value or "").strip().lower()


def rank_lawyers(
    query_text: str,
    legal_area: str | None = None,
    city: str | None = None,
    language: str | None = None,
    limit: int = 5,
):
    if not query_text.strip():
        return []

    query_embedding = embed_model.encode(query_text).tolist()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.id, p.name, p.city, p.category, p.rating, p.review_count, p.embedding,
               lp.languages
        FROM professionals p
        LEFT JOIN lawyer_profiles lp ON lp.lawyer_id = p.id
        WHERE p.embedding IS NOT NULL
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    norm_legal_area = _normalized_text(legal_area)
    norm_city = _normalized_text(city)
    norm_lang = _normalized_text(language)

    ranked = []
    for row in rows:
        pid, name, professional_city, category, rating, reviews, embedding_json, languages = row
        try:
            profile_embedding = np.array(json.loads(embedding_json))
            embedding_score = float(np.dot(query_embedding, profile_embedding))
        except Exception:
            continue

        score = embedding_score

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
        score += rating_boost

        ranked.append(
            {
                "id": pid,
                "name": name,
                "city": professional_city,
                "category": category,
                "rating": rating,
                "reviews": reviews,
                "score": score,
                "embedding_score": embedding_score,
            }
        )

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:limit]


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
        limit=limit,
    )
