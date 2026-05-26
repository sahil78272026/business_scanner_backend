"""
Export routes — CSV export with credit deduction.
"""

from fastapi import APIRouter, Depends
from app.core.dependencies import get_db, get_current_user_id
from app.models.schemas import ExportCSVRequest
from app.services import business_service

router = APIRouter(prefix="/api", tags=["Export"])


@router.post("/export-csv")
def export_csv(
    body: ExportCSVRequest,
    user_id: int = Depends(get_current_user_id),
    conn=Depends(get_db),
):
    businesses = [b.model_dump() for b in body.businesses]
    return business_service.export_csv(conn, user_id=user_id, businesses=businesses)
