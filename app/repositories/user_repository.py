"""
User repository — all database operations for the users table.
"""

from psycopg2.extras import RealDictCursor


def find_by_email(conn, email: str) -> dict | None:
    """Find a user by email address."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT id, name, email, password, provider, credits FROM users WHERE email = %s",
        (email,),
    )
    row = cur.fetchone()
    cur.close()
    return dict(row) if row else None


def find_by_id(conn, user_id: int) -> dict | None:
    """Find a user by ID."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT id, name, email, password, provider, credits, created_at FROM users WHERE id = %s",
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()
    return dict(row) if row else None


def create_user(conn, *, name: str, email: str, password: str | None = None, provider: str = "password") -> dict:
    """
    Insert a new user and return the created row.
    Password is nullable for Google sign-in users.
    """
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """
        INSERT INTO users (name, email, password, provider, created_at)
        VALUES (%s, %s, %s, %s, NOW())
        RETURNING id, credits
        """,
        (name, email, password, provider),
    )
    row = cur.fetchone()
    cur.close()
    return dict(row)


def get_credits(conn, user_id: int) -> int | None:
    """Get the credit balance for a user. Returns None if user not found."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT credits FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    return row["credits"] if row else None


def update_credits(conn, user_id: int, new_credits: int):
    """Set the credit balance for a user."""
    cur = conn.cursor()
    cur.execute("UPDATE users SET credits = %s WHERE id = %s", (new_credits, user_id))
    cur.close()
