import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any


class TokenError(ValueError):
    """Raised when a signed access token is invalid or expired."""


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
        maxmem=64 * 1024 * 1024,
    )
    return f"scrypt${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, salt_text, digest_text = encoded.split("$", 2)
        if scheme != "scrypt":
            return False
        salt = _b64decode(salt_text)
        expected = _b64decode(digest_text)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=2**14,
            r=8,
            p=1,
            maxmem=64 * 1024 * 1024,
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: str,
    role: str,
    secret: str,
    expires_in_minutes: int,
) -> str:
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "exp": int(time.time()) + expires_in_minutes * 60,
    }
    payload_text = _b64encode(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )
    signature = hmac.new(secret.encode("utf-8"), payload_text.encode("ascii"), hashlib.sha256)
    return f"{payload_text}.{_b64encode(signature.digest())}"


def decode_access_token(token: str, secret: str) -> dict[str, Any]:
    try:
        payload_text, signature_text = token.split(".", 1)
        expected = hmac.new(
            secret.encode("utf-8"), payload_text.encode("ascii"), hashlib.sha256
        ).digest()
        actual = _b64decode(signature_text)
        if not hmac.compare_digest(actual, expected):
            raise TokenError("Invalid token signature")
        payload = json.loads(_b64decode(payload_text))
        if not isinstance(payload, dict):
            raise TokenError("Invalid token payload")
        if int(payload.get("exp", 0)) < int(time.time()):
            raise TokenError("Token has expired")
        if not payload.get("sub") or not payload.get("role"):
            raise TokenError("Token is missing required claims")
        return payload
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        if isinstance(exc, TokenError):
            raise
        raise TokenError("Invalid token") from exc
