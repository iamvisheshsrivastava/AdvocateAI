import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AIConfig:
    llm_model: str
    llm_vision_model: str
    default_timeout_seconds: int
    analysis_timeout_seconds: int
    brief_timeout_seconds: int
    chat_timeout_seconds: int
    document_timeout_seconds: int


def get_ai_config() -> AIConfig:
    def _int(name: str, default: int) -> int:
        try:
            return int(os.getenv(name, str(default)))
        except ValueError:
            return default

    return AIConfig(
        llm_model=os.getenv("OPENROUTER_MODEL", "z-ai/glm-4.6"),
        llm_vision_model=os.getenv("OPENROUTER_VISION_MODEL", "z-ai/glm-4.6v"),
        default_timeout_seconds=_int("LLM_DEFAULT_TIMEOUT", 20),
        analysis_timeout_seconds=_int("LLM_ANALYSIS_TIMEOUT", 35),
        brief_timeout_seconds=_int("LLM_BRIEF_TIMEOUT", 25),
        chat_timeout_seconds=_int("LLM_CHAT_TIMEOUT", 25),
        document_timeout_seconds=_int("LLM_DOCUMENT_TIMEOUT", 30),
    )


def log_ai_event(*_args, **_kwargs) -> None:
    """No-op — telemetry removed."""
