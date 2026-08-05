# routers/admin_analytics.py
from fastapi import APIRouter, Depends

from routers.deps import require_admin
import database as db

router = APIRouter(prefix="/api/admin", tags=["admin-analytics"])


@router.get("/analytics")
def admin_get_analytics(admin=Depends(require_admin)):
    return db.get_analytics_summary()


@router.get("/student-activity")
def admin_get_student_activity(q: str = "", admin=Depends(require_admin)):
    """Har bir o'quvchi nechta nazorat testi, oddiy test va simulyator
    ishlaganini ko'rsatadigan ro'yxat (admin panel — 'Talabalar faolligi')."""
    return {"students": db.get_student_activity(q, limit=50)}
