from __future__ import annotations

import logging
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400, details: Any | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details


def handle_exceptions(fn: Callable) -> Callable:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except AppError:
            raise
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Unhandled error in %s", fn.__name__)
            raise AppError("Internal error", status_code=500, details=str(exc))

    return wrapper
