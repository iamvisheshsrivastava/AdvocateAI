import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AIConfig:
    gemini_model: str
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
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        default_timeout_seconds=_int("GEMINI_DEFAULT_TIMEOUT", 20),
        analysis_timeout_seconds=_int("GEMINI_ANALYSIS_TIMEOUT", 35),
        brief_timeout_seconds=_int("GEMINI_BRIEF_TIMEOUT", 25),
        chat_timeout_seconds=_int("GEMINI_CHAT_TIMEOUT", 25),
        document_timeout_seconds=_int("GEMINI_DOCUMENT_TIMEOUT", 30),
    )


def log_ai_event(*_args, **_kwargs) -> None:
    """No-op — telemetry removed."""
