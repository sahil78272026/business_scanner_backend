"""
Business service — orchestrates saving, retrieval, status/notes updates, and CSV export.
"""

import io
import csv
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from app.repositories import user_repository, business_repository


EXPORT_COST = 10  # Credits consumed per CSV export


def save_business(conn, *, user_id: int, data: dict) -> dict:
    """Save a business to the user's collection."""
    emails_str = ", ".join(data.get("emails", []))

    result = business_repository.save_business(
        conn,
        user_id=user_id,
        name=data["name"],
        address=data.get("address"),
        phone=data.get("phone"),
        website=data.get("website"),
        rating=data.get("rating"),
        reviews_count=data.get("reviews_count"),
        maps_url=data.get("maps_url"),
        emails_str=emails_str,
    )

    if result:
        return {"message": "Saved successfully"}
    return {"message": "Already saved"}


def get_saved_businesses(conn, user_id: int) -> list[dict]:
    """Retrieve all saved businesses for a user."""
    return business_repository.get_saved_businesses(conn, user_id)


def update_status(conn, *, user_id: int, business_id: int, status: str) -> dict:
    """Update the lead status of a saved business."""
    business_repository.update_status(
        conn, business_id=business_id, user_id=user_id, status=status
    )
    return {"success": True}


def update_notes(conn, *, user_id: int, business_id: int, notes: str) -> dict:
    """Update the notes on a saved business."""
    business_repository.update_notes(
        conn, business_id=business_id, user_id=user_id, notes=notes
    )
    return {"success": True}


def export_csv(conn, *, user_id: int, businesses: list[dict]) -> StreamingResponse:
    """
    Generate a CSV file from a list of businesses.
    Deducts credits from the user's account.
    Returns a StreamingResponse with the CSV content.
    """
    # Verify user exists and has enough credits
    user = user_repository.find_by_id(conn, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user["credits"] < EXPORT_COST:
        raise HTTPException(
            status_code=402,
            detail="Not enough credits to export. Please purchase more credits.",
        )

    if not businesses:
        raise HTTPException(status_code=400, detail="No business data provided")

    # Deduct credits
    new_credits = user["credits"] - EXPORT_COST
    user_repository.update_credits(conn, user_id, new_credits)

    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Name", "Address", "Phone", "Rating",
        "Reviews", "Website", "Google Maps URL", "Emails",
    ])

    for b in businesses:
        emails_str = ", ".join(b.get("emails", []))
        writer.writerow([
            b.get("name", ""),
            b.get("address", ""),
            b.get("phone", ""),
            b.get("rating", ""),
            b.get("reviews_count", ""),
            b.get("website", ""),
            b.get("maps_url", ""),
            emails_str,
        ])

    output.seek(0)
    csv_bytes = io.BytesIO(output.getvalue().encode("utf-8"))
    csv_bytes.seek(0)

    headers = {
        "Content-Disposition": "attachment; filename=businesses.csv",
        "X-Credits-Left": str(new_credits),
    }

    return StreamingResponse(
        csv_bytes,
        media_type="text/csv",
        headers=headers,
    )
