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
def health_check():
    return {"status": "ok", "version": "2.0.0"}
