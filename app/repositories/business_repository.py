"""
Business repository — all database operations for the saved_businesses table.
"""

from psycopg2.extras import RealDictCursor


def save_business(conn, *, user_id: int, name: str, address: str | None,
                  phone: str | None, website: str | None, rating: float | None,
                  reviews_count: int | None, maps_url: str | None,
                  emails_str: str) -> dict | None:
    """
    Insert a business into saved_businesses.
    Uses ON CONFLICT to prevent duplicates (user_id, name, address).
    Returns the inserted row or None if it already existed.
    """
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """
        INSERT INTO saved_businesses
            (user_id, name, address, phone, website, rating, reviews_count, maps_url, emails)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id, name, address) DO NOTHING
        RETURNING id
        """,
        (user_id, name, address, phone, website, rating, reviews_count, maps_url, emails_str),
    )
    result = cur.fetchone()
    cur.close()
    return dict(result) if result else None


def get_saved_businesses(conn, user_id: int) -> list[dict]:
    """Get all saved businesses for a user, ordered by most recently saved."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT * FROM saved_businesses WHERE user_id = %s ORDER BY saved_at DESC",
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()

    # Convert stored comma-separated email string back to list
    for row in rows:
        email_str = row.get("emails")
        if email_str:
            row["emails"] = [e.strip() for e in email_str.split(",")]
        else:
            row["emails"] = []

    return [dict(r) for r in rows]


def update_status(conn, *, business_id: int, user_id: int, status: str):
    """Update the lead status of a saved business."""
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE saved_businesses
        SET status = %s
        WHERE id = %s AND user_id = %s
        """,
        (status, business_id, user_id),
    )
    cur.close()


def update_notes(conn, *, business_id: int, user_id: int, notes: str):
    """Update the notes of a saved business."""
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE saved_businesses
        SET notes = %s
        WHERE id = %s AND user_id = %s
        """,
        (notes, business_id, user_id),
    )
    cur.close()
