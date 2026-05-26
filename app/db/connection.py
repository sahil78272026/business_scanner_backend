"""
Database connection pool management using psycopg2 ThreadedConnectionPool.
Replaces the per-request connection creation pattern from the Flask version.
"""

import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from app.core.config import get_settings

_pool: ThreadedConnectionPool | None = None


def init_pool(min_conn: int = 2, max_conn: int = 10):
    """Initialize the global connection pool. Called once at app startup."""
    global _pool
    settings = get_settings()
    _pool = ThreadedConnectionPool(min_conn, max_conn, settings.DATABASE_URL)


def get_connection():
    """Get a connection from the pool."""
    global _pool
    if _pool is None:
        init_pool()
    return _pool.getconn()


def release_connection(conn):
    """Return a connection back to the pool."""
    global _pool
    if _pool is not None:
        _pool.putconn(conn)


def close_pool():
    """Close all pool connections. Called at app shutdown."""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
