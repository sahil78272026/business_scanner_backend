"""
FastAPI dependencies for authentication and database access.
Injected into route handlers via Depends().
"""

from fastapi import Depends, HTTPException, Header
from typing import Optional
from psycopg2.extensions import connection as PgConnection
from app.core.security import decode_jwt
from app.db.connection import get_connection, release_connection


def get_db():
    """
    Dependency that provides a database connection from the pool.
    Auto-commits on success, rolls back on error, and always returns
    the connection to the pool.
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def get_current_user_id(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> int:
    """
    Dependency that extracts and validates the user ID from
    the Authorization: Bearer <token> header.
    Returns 401 if missing or invalid (not 422).
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Login required to perform this action.")

    token = authorization.replace("Bearer ", "")
    try:
        payload = decode_jwt(token)
        user_id = payload.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return user_id
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_optional_user_id(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Optional[int]:
    """
    Like get_current_user_id but returns None instead of raising
    when no token is present. Useful for endpoints that work for
    both logged-in and anonymous users.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "")
    try:
        payload = decode_jwt(token)
        return payload.get("id")
    except Exception:
        return None
