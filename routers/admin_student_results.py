# routers/admin_student_results.py
# "Natijalar" lentasidagi yozuvlarni ADMIN panelidan
# qo'shish/tahrirlash/o'chirish uchun.

from fastapi import APIRouter, Depends, Body

from routers.deps import require_admin
import database as db

router = APIRouter(prefix="/api/admin", tags=["admin-student-results"])


@router.get("/student-results")
def admin_list_student_results(admin=Depends(require_admin)):
    return {"results": db.get_student_results(only_active=False)}


@router.post("/student-results")
def admin_create_student_result(data: dict = Body(...), admin=Depends(require_admin)):
    return {"id": db.create_student_result(data)}


@router.put("/student-results/{result_id}")
def admin_update_student_result(result_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    db.update_student_result(result_id, data)
    return {"ok": True}


@router.delete("/student-results/{result_id}")
def admin_delete_student_result(result_id: int, admin=Depends(require_admin)):
    db.delete_student_result(result_id)
    return {"ok": True}
