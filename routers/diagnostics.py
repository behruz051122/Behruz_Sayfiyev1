# routers/diagnostics.py
import os

from fastapi import APIRouter, Depends

from routers.deps import require_admin
import database as db

router = APIRouter(prefix="/api", tags=["diagnostics"])


@router.get("/debug/db-info")
def api_debug_db_info(admin=Depends(require_admin)):
    """Ma'lumotlar bazasi qayerda saqlanayotganini tekshirish uchun diagnostika.
    Faqat admin ko'ra oladi (avvalgi versiyalarda bu ochiq edi — endi yopilgan)."""
    path = db.DB_PATH
    exists = os.path.exists(path)
    size = os.path.getsize(path) if exists else 0
    is_persistent_path = path.startswith("/data")
    course_count = len(db.get_all_courses(only_active=False))
    return {
        "db_path": path,
        "file_exists": exists,
        "file_size_bytes": size,
        "looks_persistent": is_persistent_path,
        "courses_in_database": course_count,
        "railway_db_path_env_set": os.environ.get("DB_PATH") is not None,
    }
