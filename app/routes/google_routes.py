"""
Google Maps routes — geocoding, business search, city autocomplete.

Credit costs:
  - Search:    5 credits (login required)
  - Load More: 5 credits (login required)
  - Export:    10 credits (handled in export_routes)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from app.core.dependencies import get_db, get_current_user_id
from app.models.schemas import GeocodeResponse, BusinessSearchResponse
from app.services import google_service
from app.repositories import user_repository

router = APIRouter(prefix="/api", tags=["Google"])

SEARCH_COST = 5  # Credits per search or Load More


@router.get("/geocode", response_model=GeocodeResponse)
def geocode(city: str = Query(..., description="City name to geocode")):
    coords = google_service.geocode_city(city)
    if not coords:
        raise HTTPException(status_code=404, detail="Unable to geocode city")
    return {"lat": coords[0], "lng": coords[1]}


@router.get("/businesses", response_model=BusinessSearchResponse)
def search_businesses(
    lat: float = Query(...),
    lng: float = Query(...),
    type: Optional[str] = Query(None, description="Google place type"),
    radius: int = Query(2000, ge=100, le=50000),
    keyword: Optional[str] = Query(None),
    next_page_token: Optional[str] = Query(None),
    user_id: int = Depends(get_current_user_id),
    conn=Depends(get_db),
):
    # ── Credit check ────────────────────────────────────────
    credits = user_repository.get_credits(conn, user_id)
    if credits is None:
        raise HTTPException(status_code=404, detail="User not found")

    if credits < SEARCH_COST:
        raise HTTPException(
            status_code=402,
            detail="Not enough credits. Please purchase more credits to continue searching.",
        )

    # Deduct credits
    new_credits = credits - SEARCH_COST
    user_repository.update_credits(conn, user_id, new_credits)

    # ── Fetch businesses ────────────────────────────────────
    try:
        result = google_service.fetch_businesses(
            conn,
            lat, lng,
            place_type=type,
            radius=radius,
            keyword=keyword,
            next_token=next_page_token,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Include updated credits in response
    result["credits"] = new_credits

    return result


@router.get("/autocomplete")
def autocomplete(query: Optional[str] = Query(None)):
    if not query:
        return []
    return google_service.autocomplete_city(query)
