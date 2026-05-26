"""
FastAPI application factory.
Registers CORS middleware, all route modules, and lifecycle hooks.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.connection import init_pool, close_pool
from app.routes import auth_routes, google_routes, business_routes, export_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle — initialize and close the DB pool."""
    init_pool()
    yield
    close_pool()


app = FastAPI(
    title="Business Scanner API",
    description="Lead generation tool — search businesses, scrape emails, export CSV",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins (same as the Flask version)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Credits-Left"],  # Needed for CSV export credit tracking
)

# Register route modules
app.include_router(auth_routes.router)
app.include_router(google_routes.router)
app.include_router(business_routes.router)
app.include_router(export_routes.router)


@app.get("/", tags=["Health"])
def root():
    """Lightweight ping — no DB hit. Ideal for cron keep-alive."""
    from datetime import datetime, timezone
    return {"status": "ok", "version": "2.0.0", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/health", tags=["Health"])
def health_check():
    """Full health check — pings the database with SELECT 1."""
    from datetime import datetime, timezone
    from app.db.connection import get_connection, release_connection

    result = {"app": "ok", "db": "unknown", "version": "2.0.0", "timestamp": datetime.now(timezone.utc).isoformat()}

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        release_connection(conn)
        result["db"] = "ok"
    except Exception as e:
        result["db"] = f"error: {str(e)}"

    return result
