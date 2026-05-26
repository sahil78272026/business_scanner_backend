"""
Authentication routes — register, login, Google OAuth, profile, credits.
"""

from fastapi import APIRouter, Depends
from app.core.dependencies import get_db, get_current_user_id
from app.models.schemas import (
    RegisterRequest, LoginRequest, GoogleAuthRequest,
    AuthResponse, UserProfile, UserProfileFull,
    CreditsResponse, ErrorResponse,
)
from app.services import auth_service
from app.repositories import user_repository

router = APIRouter(prefix="/api", tags=["Auth"])


@router.post("/register", response_model=AuthResponse)
def register(body: RegisterRequest, conn=Depends(get_db)):
    return auth_service.register(
        conn, name=body.name, email=body.email, password=body.password
    )


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, conn=Depends(get_db)):
    return auth_service.login(conn, email=body.email, password=body.password)


@router.post("/auth/google", response_model=AuthResponse)
def google_login(body: GoogleAuthRequest, conn=Depends(get_db)):
    return auth_service.google_auth(conn, credential=body.credential)


@router.get("/me", response_model=UserProfile)
def get_me(user_id: int = Depends(get_current_user_id), conn=Depends(get_db)):
    user = user_repository.find_by_id(conn, user_id)
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user["id"], "name": user.get("name"), "email": user["email"]}


@router.get("/profile", response_model=UserProfileFull)
def get_profile(user_id: int = Depends(get_current_user_id), conn=Depends(get_db)):
    user = user_repository.find_by_id(conn, user_id)
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user["id"],
        "email": user["email"],
        "created_at": user.get("created_at"),
    }


@router.get("/credits", response_model=CreditsResponse)
def get_credits(user_id: int = Depends(get_current_user_id), conn=Depends(get_db)):
    credits = user_repository.get_credits(conn, user_id)
    if credits is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
    return {"credits": credits}
