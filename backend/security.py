import hashlib
import hmac
import secrets


HASH_ALGORITHM = "pbkdf2_sha256"
HASH_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        HASH_ITERATIONS,
    )
    return f"{HASH_ALGORITHM}${HASH_ITERATIONS}${salt}${digest.hex()}"


def is_legacy_password_hash(stored_password: str | None) -> bool:
    return bool(stored_password) and not str(stored_password).startswith(f"{HASH_ALGORITHM}$")


def verify_password(password: str, stored_password: str | None) -> bool:
    if not stored_password:
        return False

    stored_password = str(stored_password)
    if is_legacy_password_hash(stored_password):
        return hmac.compare_digest(stored_password, password)

    try:
        algorithm, iterations, salt, expected_digest = stored_password.split("$", 3)
        if algorithm != HASH_ALGORITHM:
            return False

        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        )
    except (TypeError, ValueError):
        return False

    return hmac.compare_digest(digest.hex(), expected_digest)
