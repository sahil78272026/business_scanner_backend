"""
Business routes — save, list, update status/notes, scrape emails.
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.core.dependencies import get_db, get_current_user_id
from app.models.schemas import (
    SaveBusinessRequest, UpdateStatusRequest, UpdateNotesRequest,
    SavedBusinessOut, EmailScrapeResponse,
)
from app.services import business_service, email_scraper_service

router = APIRouter(prefix="/api", tags=["Businesses"])


@router.post("/save-business")
def save_business(
    body: SaveBusinessRequest,
    user_id: int = Depends(get_current_user_id),
    conn=Depends(get_db),
):
    return business_service.save_business(conn, user_id=user_id, data=body.model_dump())


@router.get("/saved-businesses", response_model=list[SavedBusinessOut])
def get_saved_businesses(
    user_id: int = Depends(get_current_user_id),
    conn=Depends(get_db),
):
    return business_service.get_saved_businesses(conn, user_id)


@router.post("/update-status")
def update_status(
    body: UpdateStatusRequest,
    user_id: int = Depends(get_current_user_id),
    conn=Depends(get_db),
):
    return business_service.update_status(
        conn, user_id=user_id, business_id=body.id, status=body.status
    )


@router.post("/update-notes")
def update_notes(
    body: UpdateNotesRequest,
    user_id: int = Depends(get_current_user_id),
    conn=Depends(get_db),
):
    return business_service.update_notes(
        conn, user_id=user_id, business_id=body.id, notes=body.notes
    )


@router.get("/scrape-email", response_model=EmailScrapeResponse)
def scrape_email(url: Optional[str] = Query(None)):
    if not url:
        return {"emails": []}
    try:
        emails = email_scraper_service.extract_emails_from_website(url)
        return {"emails": emails}
    except Exception:
        return {"emails": []}
