"""
Authentication service — handles registration, login, and Google OAuth logic.
"""

from fastapi import HTTPException
from google.oauth2 import id_token
from google.auth.transport import requests as grequests

from app.core.config import get_settings
from app.core.security import hash_password, verify_password, generate_jwt
from app.repositories import user_repository


def register(conn, *, name: str, email: str, password: str) -> dict:
    """
    Register a new user with email/password.
    Returns {"token": ..., "credits": ...} on success.
    Raises HTTPException on validation failures.
    """
    name = name.strip()
    email = email.strip().lower()

    if not name or not email or not password:
        raise HTTPException(status_code=400, detail="name, email and password required")

    existing = user_repository.find_by_email(conn, email)
    if existing:
        if existing.get("provider") == "google":
            raise HTTPException(
                status_code=400,
                detail="Account exists with Google Sign-in. Use Google login.",
            )
        raise HTTPException(status_code=400, detail="User already exists")

    hashed = hash_password(password)
    user = user_repository.create_user(conn, name=name, email=email, password=hashed, provider="password")

    token = generate_jwt({"id": user["id"], "email": email})
    return {"token": token, "credits": user["credits"]}


def login(conn, *, email: str, password: str) -> dict:
    """
    Authenticate a user with email/password.
    Returns {"token": ..., "credits": ...} on success.
    """
    email = (email or "").strip().lower()
    if not email or not password:
        raise HTTPException(status_code=400, detail="email and password required")

    user = user_repository.find_by_email(conn, email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    provider = user.get("provider") or "password"
    if provider == "google":
        raise HTTPException(
            status_code=400,
            detail="This account uses Google Sign-in. Please use Google login.",
        )

    hashed = user.get("password")
    if not hashed:
        raise HTTPException(status_code=400, detail="No password set for this account")

    # Password verification — was commented out in the Flask version (security fix)
    if not verify_password(password, hashed):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = generate_jwt({"id": user["id"], "email": email})
    return {"token": token, "credits": user["credits"]}


def google_auth(conn, *, credential: str) -> dict:
    """
    Verify a Google ID token credential, create or find the user,
    and return a JWT + credits.
    """
    settings = get_settings()

    try:
        idinfo = id_token.verify_oauth2_token(
            credential, grequests.Request(), settings.GOOGLE_CLIENT_ID
        )
        email = idinfo.get("email")
        name = idinfo.get("name") or ""

        if not email:
            raise HTTPException(status_code=400, detail="Google did not provide email")

        user = user_repository.find_by_email(conn, email)

        if user:
            user_id = user["id"]
            credits = user["credits"]
        else:
            new_user = user_repository.create_user(
                conn, name=name, email=email, provider="google"
            )
            user_id = new_user["id"]
            credits = new_user["credits"]

        token = generate_jwt({"id": user_id, "email": email})
        return {"token": token, "credits": credits}

    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid Google token")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Google auth failed")
