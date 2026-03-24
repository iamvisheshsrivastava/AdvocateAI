import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    from hydra import compose, initialize_config_dir
except Exception:  # pragma: no cover - optional dependency
    compose = None
    initialize_config_dir = None

try:
    import mlflow
except Exception:  # pragma: no cover - optional dependency
    mlflow = None

try:
    import wandb
except Exception:  # pragma: no cover - optional dependency
    wandb = None


@dataclass(frozen=True)
class AIConfig:
    gemini_model: str = "gemini-2.5-flash"
    default_timeout_seconds: int = 20
    analysis_timeout_seconds: int = 35
    brief_timeout_seconds: int = 25
    chat_timeout_seconds: int = 25
    document_timeout_seconds: int = 30


@dataclass(frozen=True)
class TrackingConfig:
    enabled: bool = True
    mlflow_enabled: bool = True
    mlflow_tracking_uri: str | None = None
    mlflow_experiment: str = "AdvocateAI"
    wandb_enabled: bool = False
    wandb_project: str = "AdvocateAI"
    wandb_entity: str | None = None
    wandb_mode: str = "offline"
    log_prompts: bool = False


@dataclass(frozen=True)
class MLOpsConfig:
    ai: AIConfig = field(default_factory=AIConfig)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: Any, default: int) -> int:
    if value is None:
        return default
    try:
        text = str(value).strip()
        return default if not text else int(text)
    except Exception:
        return default


def _as_text(value: Any, default: str) -> str:
    text = str(value).strip() if value is not None else ""
    return text or default


def _mapping_get(mapping: Any, key: str, default: Any = None) -> Any:
    if mapping is None:
        return default
    if isinstance(mapping, dict):
        return mapping.get(key, default)
    try:
        return mapping[key]
    except Exception:
        return getattr(mapping, key, default)


def _load_config_from_hydra() -> MLOpsConfig:
    config_dir = Path(__file__).resolve().parent.parent / "conf"
    if compose is None or initialize_config_dir is None or not config_dir.exists():
        return MLOpsConfig()

    try:
        with initialize_config_dir(version_base=None, config_dir=str(config_dir)):
            raw = compose(config_name="mlops")
    except Exception:
        return MLOpsConfig()

    ai_section = _mapping_get(raw, "ai", {})
    tracking_section = _mapping_get(raw, "tracking", {})

    return MLOpsConfig(
        ai=AIConfig(
            gemini_model=_as_text(_mapping_get(ai_section, "gemini_model", "gemini-2.5-flash"), "gemini-2.5-flash"),
            default_timeout_seconds=_as_int(_mapping_get(ai_section, "default_timeout_seconds", 20), 20),
            analysis_timeout_seconds=_as_int(_mapping_get(ai_section, "analysis_timeout_seconds", 35), 35),
            brief_timeout_seconds=_as_int(_mapping_get(ai_section, "brief_timeout_seconds", 25), 25),
            chat_timeout_seconds=_as_int(_mapping_get(ai_section, "chat_timeout_seconds", 25), 25),
            document_timeout_seconds=_as_int(_mapping_get(ai_section, "document_timeout_seconds", 30), 30),
        ),
        tracking=TrackingConfig(
            enabled=_as_bool(_mapping_get(tracking_section, "enabled", True), True),
            mlflow_enabled=_as_bool(_mapping_get(tracking_section, "mlflow_enabled", True), True),
            mlflow_tracking_uri=_as_text(_mapping_get(tracking_section, "mlflow_tracking_uri", ""), "") or None,
            mlflow_experiment=_as_text(_mapping_get(tracking_section, "mlflow_experiment", "AdvocateAI"), "AdvocateAI"),
            wandb_enabled=_as_bool(_mapping_get(tracking_section, "wandb_enabled", False), False),
            wandb_project=_as_text(_mapping_get(tracking_section, "wandb_project", "AdvocateAI"), "AdvocateAI"),
            wandb_entity=_as_text(_mapping_get(tracking_section, "wandb_entity", ""), "") or None,
            wandb_mode=_as_text(_mapping_get(tracking_section, "wandb_mode", "offline"), "offline"),
            log_prompts=_as_bool(_mapping_get(tracking_section, "log_prompts", False), False),
        ),
    )


@lru_cache(maxsize=1)
def get_mlops_config() -> MLOpsConfig:
    config = _load_config_from_hydra()

    ai = config.ai
    tracking = config.tracking

    return MLOpsConfig(
        ai=AIConfig(
            gemini_model=_as_text(os.getenv("GEMINI_MODEL"), ai.gemini_model),
            default_timeout_seconds=_as_int(os.getenv("GEMINI_DEFAULT_TIMEOUT"), ai.default_timeout_seconds),
            analysis_timeout_seconds=_as_int(os.getenv("GEMINI_ANALYSIS_TIMEOUT"), ai.analysis_timeout_seconds),
            brief_timeout_seconds=_as_int(os.getenv("GEMINI_BRIEF_TIMEOUT"), ai.brief_timeout_seconds),
            chat_timeout_seconds=_as_int(os.getenv("GEMINI_CHAT_TIMEOUT"), ai.chat_timeout_seconds),
            document_timeout_seconds=_as_int(os.getenv("GEMINI_DOCUMENT_TIMEOUT"), ai.document_timeout_seconds),
        ),
        tracking=TrackingConfig(
            enabled=_as_bool(os.getenv("MLOPS_ENABLED"), tracking.enabled),
            mlflow_enabled=_as_bool(os.getenv("MLFLOW_ENABLED"), tracking.mlflow_enabled),
            mlflow_tracking_uri=os.getenv("MLFLOW_TRACKING_URI") or tracking.mlflow_tracking_uri,
            mlflow_experiment=_as_text(os.getenv("MLFLOW_EXPERIMENT_NAME"), tracking.mlflow_experiment),
            wandb_enabled=_as_bool(os.getenv("WANDB_ENABLED"), tracking.wandb_enabled),
            wandb_project=_as_text(os.getenv("WANDB_PROJECT"), tracking.wandb_project),
            wandb_entity=os.getenv("WANDB_ENTITY") or tracking.wandb_entity,
            wandb_mode=_as_text(os.getenv("WANDB_MODE"), tracking.wandb_mode),
            log_prompts=_as_bool(os.getenv("MLOPS_LOG_PROMPTS"), tracking.log_prompts),
        ),
    )


def get_ai_config() -> AIConfig:
    return get_mlops_config().ai


def get_tracking_config() -> TrackingConfig:
    return get_mlops_config().tracking


def _resolve_mlflow_tracking_uri(config: TrackingConfig) -> str:
    if config.mlflow_tracking_uri:
        return config.mlflow_tracking_uri

    tracking_dir = Path(__file__).resolve().parents[2] / "mlruns"
    tracking_dir.mkdir(parents=True, exist_ok=True)
    return tracking_dir.resolve().as_uri()


def _hash_actor_key(actor_key: str) -> str:
    return hashlib.sha256((actor_key or "anonymous").encode("utf-8")).hexdigest()[:12]


def _safe_metadata(metadata: dict[str, Any] | None) -> dict[str, str]:
    if not metadata:
        return {}

    safe: dict[str, str] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            safe[key] = str(value)
            continue
        if isinstance(value, (list, tuple, set)):
            safe[key] = json.dumps(list(value)[:10], ensure_ascii=True)
            continue
        if isinstance(value, dict):
            preview = {item_key: item_value for item_key, item_value in list(value.items())[:10]}
            safe[key] = json.dumps(preview, ensure_ascii=True)
            continue
        safe[key] = str(value)
    return safe


def _log_to_mlflow(
    event_name: str,
    *,
    status: str,
    duration_ms: float,
    input_text: str,
    output_text: str,
    actor_key: str,
    model_name: str,
    cache_hit: bool,
    metadata: dict[str, Any] | None,
    error: Exception | None,
) -> None:
    config = get_tracking_config()
    if not config.enabled or not config.mlflow_enabled or mlflow is None:
        return

    mlflow.set_tracking_uri(_resolve_mlflow_tracking_uri(config))
    mlflow.set_experiment(config.mlflow_experiment)

    params = {
        "event_name": event_name,
        "status": status,
        "model_name": model_name,
        "cache_hit": str(bool(cache_hit)).lower(),
        "actor_hash": _hash_actor_key(actor_key),
        "input_chars": len(input_text or ""),
        "output_chars": len(output_text or ""),
    }
    if error is not None:
        params["error_type"] = error.__class__.__name__
        params["error_message"] = str(error)[:200]

    tags = _safe_metadata(metadata)
    tags["actor_hash"] = _hash_actor_key(actor_key)
    tags["status"] = status
    tags["cache_hit"] = str(bool(cache_hit)).lower()

    with mlflow.start_run(run_name=event_name):
        mlflow.log_params(params)
        mlflow.log_metrics({"latency_ms": round(duration_ms, 2)})
        mlflow.set_tags(tags)


def _log_to_wandb(
    event_name: str,
    *,
    status: str,
    duration_ms: float,
    input_text: str,
    output_text: str,
    actor_key: str,
    model_name: str,
    cache_hit: bool,
    metadata: dict[str, Any] | None,
    error: Exception | None,
) -> None:
    config = get_tracking_config()
    if not config.enabled or not config.wandb_enabled or wandb is None:
        return

    run = wandb.init(
        project=config.wandb_project,
        entity=config.wandb_entity,
        mode=config.wandb_mode,
        reinit=True,
        name=event_name,
    )
    try:
        payload = {
            "event_name": event_name,
            "status": status,
            "latency_ms": round(duration_ms, 2),
            "model_name": model_name,
            "cache_hit": bool(cache_hit),
            "actor_hash": _hash_actor_key(actor_key),
            "input_chars": len(input_text or ""),
            "output_chars": len(output_text or ""),
        }
        if error is not None:
            payload["error_type"] = error.__class__.__name__
            payload["error_message"] = str(error)[:200]
        payload.update(_safe_metadata(metadata))
        run.log(payload)
    finally:
        run.finish()


def log_ai_event(
    event_name: str,
    *,
    started_at: float | None = None,
    status: str = "success",
    input_text: str = "",
    output_text: str = "",
    actor_key: str = "anonymous",
    model_name: str | None = None,
    cache_hit: bool = False,
    metadata: dict[str, Any] | None = None,
    error: Exception | None = None,
) -> None:
    config = get_mlops_config()
    if not config.tracking.enabled:
        return

    duration_ms = (time.perf_counter() - started_at) * 1000 if started_at is not None else 0.0
    resolved_model_name = model_name or config.ai.gemini_model

    _log_to_mlflow(
        event_name,
        status=status,
        duration_ms=duration_ms,
        input_text=input_text,
        output_text=output_text,
        actor_key=actor_key,
        model_name=resolved_model_name,
        cache_hit=cache_hit,
        metadata=metadata,
        error=error,
    )
    _log_to_wandb(
        event_name,
        status=status,
        duration_ms=duration_ms,
        input_text=input_text,
        output_text=output_text,
        actor_key=actor_key,
        model_name=resolved_model_name,
        cache_hit=cache_hit,
        metadata=metadata,
        error=error,
    )