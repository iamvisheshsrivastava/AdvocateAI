from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from random import Random
from typing import Any

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from db.database import get_db_connection
from services.matching_service import recommend_lawyers_for_case
from logging_config import get_logger

logger = get_logger(__name__)


ARTIFACT_DIR = Path(__file__).resolve().parent.parent / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "lawyer_match_model.joblib"
MANIFEST_PATH = ARTIFACT_DIR / "lawyer_match_model_manifest.json"
RANDOM_SEED = 42


@dataclass(frozen=True)
class CaseRecord:
    case_id: int
    legal_area: str
    city: str
    urgency: str


@dataclass(frozen=True)
class LawyerRecord:
    lawyer_id: int
    name: str
    city: str
    category: str
    rating: float
    review_count: int
    practice_areas: str
    languages: str
    experience_years: int
    response_time_hours: float
    applications_sent: int
    cases_accepted: int
    responsiveness_score: float
    availability_status: str


def _text(value: Any) -> str:
    return str(value or "").strip()


def _lower(value: Any) -> str:
    return _text(value).lower()


def _token_set(value: str) -> set[str]:
    text = _lower(value)
    return {token for token in text.replace(",", " ").split() if token}


def _has_overlap(left: str, right: str) -> int:
    return int(bool(_token_set(left).intersection(_token_set(right))))


def _build_features(case: CaseRecord, lawyer: LawyerRecord) -> dict[str, Any]:
    case_legal_area = _text(case.legal_area)
    case_city = _text(case.city)
    lawyer_city = _text(lawyer.city)
    lawyer_category = _text(lawyer.category)
    practice_areas = _text(lawyer.practice_areas)

    return {
        "case_legal_area": case_legal_area,
        "case_city": case_city,
        "case_urgency": _text(case.urgency),
        "lawyer_city": lawyer_city,
        "lawyer_category": lawyer_category,
        "lawyer_practice_areas": practice_areas,
        "lawyer_languages": _text(lawyer.languages),
        "lawyer_availability_status": _text(lawyer.availability_status),
        "lawyer_rating": float(lawyer.rating or 0.0),
        "lawyer_review_count": int(lawyer.review_count or 0),
        "lawyer_experience_years": int(lawyer.experience_years or 0),
        "lawyer_response_time_hours": float(lawyer.response_time_hours or 0.0),
        "lawyer_applications_sent": int(lawyer.applications_sent or 0),
        "lawyer_cases_accepted": int(lawyer.cases_accepted or 0),
        "lawyer_responsiveness_score": float(lawyer.responsiveness_score or 0.0),
        "city_match": int(_lower(case_city) == _lower(lawyer_city) and bool(case_city)),
        "legal_area_overlap": _has_overlap(case_legal_area, lawyer_category + " " + practice_areas),
    }


def _fetch_cases() -> dict[int, CaseRecord]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT case_id, legal_area, city, urgency
        FROM cases
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    cases: dict[int, CaseRecord] = {}
    for row in rows:
        cases[int(row[0])] = CaseRecord(
            case_id=int(row[0]),
            legal_area=_text(row[1]),
            city=_text(row[2]),
            urgency=_text(row[3]) or "Medium",
        )
    return cases


def _fetch_lawyers() -> dict[int, LawyerRecord]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.id,
               p.name,
               p.city,
               p.category,
               p.rating,
               p.review_count,
               lp.practice_areas,
               lp.languages,
               lp.experience_years,
               lp.response_time_hours,
               lp.applications_sent,
               lp.cases_accepted,
               lp.responsiveness_score,
               lp.availability_status
        FROM professionals p
        LEFT JOIN lawyer_profiles lp ON lp.lawyer_id = p.id
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    lawyers: dict[int, LawyerRecord] = {}
    for row in rows:
        lawyer_id = int(row[0])
        lawyers[lawyer_id] = LawyerRecord(
            lawyer_id=lawyer_id,
            name=_text(row[1]) or f"Lawyer {lawyer_id}",
            city=_text(row[2]),
            category=_text(row[3]),
            rating=float(row[4] or 0.0),
            review_count=int(row[5] or 0),
            practice_areas=_text(row[6]),
            languages=_text(row[7]),
            experience_years=int(row[8] or 0),
            response_time_hours=float(row[9] or 0.0),
            applications_sent=int(row[10] or 0),
            cases_accepted=int(row[11] or 0),
            responsiveness_score=float(row[12] or 0.0),
            availability_status=_text(row[13]) or "available",
        )
    return lawyers


def _fetch_case_applications() -> list[tuple[int, int]]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT case_id, lawyer_id
        FROM case_applications
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [(int(row[0]), int(row[1])) for row in rows]


def _build_training_dataframe(max_negatives_per_case: int = 20) -> tuple[pd.DataFrame, pd.Series]:
    rng = Random(RANDOM_SEED)
    cases = _fetch_cases()
    lawyers = _fetch_lawyers()
    positives = _fetch_case_applications()

    if not cases or not lawyers or not positives:
        raise ValueError(
            "Insufficient historical data. Need cases, lawyers, and case applications before training."
        )

    labels_lookup = {(case_id, lawyer_id) for case_id, lawyer_id in positives}
    rows: list[dict[str, Any]] = []

    for case_id, case in cases.items():
        candidate_lawyers = list(lawyers.values())
        if not candidate_lawyers:
            continue

        positive_lawyers = [lawyers[lawyer_id] for current_case_id, lawyer_id in positives if current_case_id == case_id and lawyer_id in lawyers]
        if not positive_lawyers:
            continue

        for lawyer in positive_lawyers:
            item = _build_features(case, lawyer)
            item["label"] = 1
            item["case_id"] = case_id
            item["lawyer_id"] = lawyer.lawyer_id
            rows.append(item)

        negative_pool = [
            lawyer for lawyer in candidate_lawyers if (case_id, lawyer.lawyer_id) not in labels_lookup
        ]
        rng.shuffle(negative_pool)
        for lawyer in negative_pool[:max_negatives_per_case]:
            item = _build_features(case, lawyer)
            item["label"] = 0
            item["case_id"] = case_id
            item["lawyer_id"] = lawyer.lawyer_id
            rows.append(item)

    if not rows:
        raise ValueError("No trainable rows could be generated from current data.")

    df = pd.DataFrame(rows)
    if df["label"].nunique() < 2:
        raise ValueError("Training labels contain only one class. Need both positive and negative examples.")

    y = df["label"]
    x = df.drop(columns=["label"])
    return x, y


def _build_pipeline() -> Pipeline:
    categorical_columns = [
        "case_legal_area",
        "case_city",
        "case_urgency",
        "lawyer_city",
        "lawyer_category",
        "lawyer_practice_areas",
        "lawyer_languages",
        "lawyer_availability_status",
    ]
    numeric_columns = [
        "lawyer_rating",
        "lawyer_review_count",
        "lawyer_experience_years",
        "lawyer_response_time_hours",
        "lawyer_applications_sent",
        "lawyer_cases_accepted",
        "lawyer_responsiveness_score",
        "city_match",
        "legal_area_overlap",
    ]

    preprocessor = ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore"), categorical_columns),
            ("numeric", StandardScaler(), numeric_columns),
        ]
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "model",
                LogisticRegression(
                    max_iter=1200,
                    class_weight="balanced",
                    random_state=RANDOM_SEED,
                ),
            ),
        ]
    )


def _compute_metrics(y_true: pd.Series, y_pred: list[int], y_prob: list[float]) -> dict[str, float]:
    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }
    if len(set(y_true.tolist())) > 1:
        metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob))
    return metrics


def train_lawyer_match_model(max_negatives_per_case: int = 20) -> dict[str, Any]:
    x, y = _build_training_dataframe(max_negatives_per_case=max_negatives_per_case)
    pipeline = _build_pipeline()

    use_holdout = len(x) >= 30 and y.value_counts().min() >= 2
    if use_holdout:
        x_train, x_test, y_train, y_test = train_test_split(
            x,
            y,
            test_size=0.25,
            stratify=y,
            random_state=RANDOM_SEED,
        )
        pipeline.fit(x_train, y_train)
        y_prob = pipeline.predict_proba(x_test)[:, 1]
        y_pred = [1 if value >= 0.5 else 0 for value in y_prob]
        metrics = _compute_metrics(y_test, y_pred, y_prob.tolist())
        eval_rows = len(x_test)
        train_rows = len(x_train)
    else:
        pipeline.fit(x, y)
        y_prob = pipeline.predict_proba(x)[:, 1]
        y_pred = [1 if value >= 0.5 else 0 for value in y_prob]
        metrics = _compute_metrics(y, y_pred, y_prob.tolist())
        eval_rows = len(x)
        train_rows = len(x)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)

    manifest = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "model_path": str(MODEL_PATH),
        "metrics": metrics,
        "train_rows": train_rows,
        "eval_rows": eval_rows,
        "total_rows": len(x),
        "class_balance": {
            "negative": int((y == 0).sum()),
            "positive": int((y == 1).sum()),
        },
        "max_negatives_per_case": max_negatives_per_case,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    return manifest


def _load_model() -> Pipeline | None:
    if not MODEL_PATH.exists():
        return None
    try:
        loaded = joblib.load(MODEL_PATH)
        if isinstance(loaded, Pipeline):
            return loaded
    except Exception:
        logger.exception("Failed to load ML matching model")
        return None
    return None


def get_model_status() -> dict[str, Any]:
    model = _load_model()
    status = {
        "trained": model is not None,
        "model_path": str(MODEL_PATH),
        "manifest_path": str(MANIFEST_PATH),
    }
    if MANIFEST_PATH.exists():
        try:
            status["manifest"] = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except Exception:
            logger.exception("Failed to read model manifest")
            status["manifest"] = None
    return status


def _fetch_case(case_id: int) -> CaseRecord | None:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT case_id, legal_area, city, urgency
        FROM cases
        WHERE case_id = %s
        """,
        (case_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    return CaseRecord(
        case_id=int(row[0]),
        legal_area=_text(row[1]),
        city=_text(row[2]),
        urgency=_text(row[3]) or "Medium",
    )


def _model_match_reasons(case: CaseRecord, lawyer: LawyerRecord, model_score: float) -> list[str]:
    reasons: list[str] = []
    if _lower(case.city) and _lower(case.city) == _lower(lawyer.city):
        reasons.append(f"City match: {lawyer.city}.")
    if _has_overlap(case.legal_area, f"{lawyer.category} {lawyer.practice_areas}"):
        reasons.append("Legal area aligns with the lawyer profile.")
    if lawyer.responsiveness_score >= 0.65:
        reasons.append("High responsiveness based on historical platform activity.")
    if model_score >= 0.7:
        reasons.append("Model confidence is strong for this case-lawyer pair.")
    if not reasons:
        reasons.append("Selected by baseline supervised matching model.")
    return reasons[:4]


def recommend_lawyers_for_case_ml(case_id: int, limit: int = 5) -> dict[str, Any]:
    model = _load_model()
    if model is None:
        return {
            "model_used": "heuristic",
            "trained": False,
            "items": recommend_lawyers_for_case(case_id, limit=limit),
        }

    case = _fetch_case(case_id)
    lawyers = _fetch_lawyers()
    if case is None or not lawyers:
        return {
            "model_used": "baseline_logistic_regression",
            "trained": True,
            "items": [],
        }

    feature_rows: list[dict[str, Any]] = []
    lawyer_by_id: dict[int, LawyerRecord] = {}
    for lawyer in lawyers.values():
        if _lower(lawyer.availability_status) == "not accepting cases":
            continue
        feature = _build_features(case, lawyer)
        feature["lawyer_id"] = lawyer.lawyer_id
        feature_rows.append(feature)
        lawyer_by_id[lawyer.lawyer_id] = lawyer

    if not feature_rows:
        return {
            "model_used": "baseline_logistic_regression",
            "trained": True,
            "items": [],
        }

    frame = pd.DataFrame(feature_rows)
    predict_frame = frame.drop(columns=["lawyer_id"])
    probabilities = model.predict_proba(predict_frame)[:, 1]

    ranked: list[dict[str, Any]] = []
    for idx, probability in enumerate(probabilities):
        lawyer_id = int(frame.iloc[idx]["lawyer_id"])
        lawyer = lawyer_by_id.get(lawyer_id)
        if lawyer is None:
            continue

        score = float(probability)
        ranked.append(
            {
                "id": lawyer.lawyer_id,
                "lawyer_id": lawyer.lawyer_id,
                "name": lawyer.name,
                "city": lawyer.city,
                "category": lawyer.category,
                "rating": lawyer.rating,
                "reviews": lawyer.review_count,
                "match_score": score,
                "model_score": score,
                "availability_status": lawyer.availability_status,
                "responsiveness_score": lawyer.responsiveness_score,
                "match_reason": _model_match_reasons(case, lawyer, score),
            }
        )

    ranked.sort(key=lambda item: item["match_score"], reverse=True)
    return {
        "model_used": "baseline_logistic_regression",
        "trained": True,
        "items": ranked[: max(1, min(limit, 20))],
    }
