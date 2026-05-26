"""
JWT token generation/verification and password hashing utilities.
"""

import jwt
import bcrypt
from datetime import datetime, timedelta
from app.core.config import get_settings


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def generate_jwt(payload: dict) -> str:
    """Generate a JWT token with an expiration claim."""
    settings = get_settings()
    data = payload.copy()
    data["exp"] = datetime.utcnow() + timedelta(seconds=settings.JWT_EXP)
    token = jwt.encode(data, settings.APP_SECRET, algorithm="HS256")
    # PyJWT 2.x may return bytes in some versions
    return token if isinstance(token, str) else token.decode("utf-8")


def decode_jwt(token: str) -> dict:
    """Decode and verify a JWT token. Raises on invalid/expired tokens."""
    settings = get_settings()
    return jwt.decode(token, settings.APP_SECRET, algorithms=["HS256"])
