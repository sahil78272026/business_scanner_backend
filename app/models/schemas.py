"""
Pydantic models for request validation and response serialization.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


# ─── Auth Schemas ────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class GoogleAuthRequest(BaseModel):
    credential: str


class AuthResponse(BaseModel):
    token: str
    credits: int


class ErrorResponse(BaseModel):
    error: str


# ─── Business Schemas ───────────────────────────────────────

class BusinessItem(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    website: Optional[str] = None
    maps_url: Optional[str] = None
    emails: list[str] = []
    types: list[str] = []


class BusinessSearchResponse(BaseModel):
    businesses: list[BusinessItem]
    next_page_token: Optional[str] = None
    credits: Optional[int] = None  # Returned after credit-consuming actions


class SaveBusinessRequest(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    maps_url: Optional[str] = None
    emails: list[str] = []


class UpdateStatusRequest(BaseModel):
    id: int
    status: str


class UpdateNotesRequest(BaseModel):
    id: int
    notes: str


class SavedBusinessOut(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    emails: list[str] = []
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    maps_url: Optional[str] = None
    status: str = "not_contacted"
    notes: str = ""
    saved_at: Optional[datetime] = None


# ─── Export Schemas ──────────────────────────────────────────

class ExportCSVRequest(BaseModel):
    businesses: list[BusinessItem]


# ─── User Schemas ───────────────────────────────────────────

class UserProfile(BaseModel):
    id: int
    name: Optional[str] = None
    email: str


class UserProfileFull(BaseModel):
    id: int
    email: str
    created_at: Optional[datetime] = None


class CreditsResponse(BaseModel):
    credits: int


# ─── Geocode Schemas ────────────────────────────────────────

class GeocodeResponse(BaseModel):
    lat: float
    lng: float


class EmailScrapeResponse(BaseModel):
    emails: list[str]
