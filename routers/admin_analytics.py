# routers/admin_analytics.py
from fastapi import APIRouter, Depends

from routers.deps import require_admin
import database as db

router = APIRouter(prefix="/api/admin", tags=["admin-analytics"])


@router.get("/analytics")
def admin_get_analytics(admin=Depends(require_admin)):
    return db.get_analytics_summary()
