# routers/admin_control_tests.py
# Nazorat testiga o'quvchilarni BEVOSITA tayinlash (kursdan mustaqil ruxsat)
# va admin panelda talaba qidirish uchun endpointlar.

from fastapi import APIRouter, Depends, Body, HTTPException

from routers.deps import require_admin
import database as db

router = APIRouter(prefix="/api/admin", tags=["admin-control-tests"])


@router.get("/control-tests/{test_id}/access")
def admin_list_control_access(test_id: int, admin=Depends(require_admin)):
    test = db.get_test(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test topilmadi")
    return {"access": db.get_control_test_access_list(test_id)}


@router.post("/control-tests/{test_id}/access")
def admin_grant_control_access(test_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    test = db.get_test(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test topilmadi")
    telegram_id = int(data["telegram_id"])
    # Talaba hali botga umuman kirmagan bo'lishi ham mumkin (masalan admin
    # uni Telegram ID orqali oldindan qo'shmoqchi) — shu sabab foydalanuvchi
    # yozuvi mavjudligini kafolatlab qo'yamiz.
    db.get_or_create_user(telegram_id, data.get("first_name") or "Foydalanuvchi", data.get("username"))
    db.assign_control_test_access(test_id, telegram_id)
    return {"ok": True}


@router.delete("/control-tests/{test_id}/access/{telegram_id}")
def admin_revoke_control_access(test_id: int, telegram_id: int, admin=Depends(require_admin)):
    db.revoke_control_test_access(test_id, telegram_id)
    return {"ok": True}


# ---------- Nazorat testini KURSLARGA bog'lash (avtomatik ochilish) ----------

@router.get("/control-tests/{test_id}/courses")
def admin_list_control_test_courses(test_id: int, admin=Depends(require_admin)):
    """Shu nazorat testi qaysi kurslarga bog'langan — ya'ni qaysi guruhga
    qo'shilgan o'quvchilarga u AVTOMATIK ochiladi."""
    test = db.get_test(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test topilmadi")
    return {"courses": db.get_control_test_courses(test_id),
            "course_ids": db.get_control_test_course_ids(test_id)}


@router.put("/control-tests/{test_id}/courses")
def admin_set_control_test_courses(test_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    """Bog'langan kurslar ro'yxatini to'liq almashtiradi. Shu kurslardan
    birortasiga yozilgan har bir o'quvchiga test avtomatik ochiladi —
    o'qituvchi ularni birma-bir qo'lda qo'shishi shart emas."""
    test = db.get_test(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test topilmadi")
    course_ids = data.get("course_ids") or []
    if not isinstance(course_ids, list):
        raise HTTPException(status_code=400, detail="course_ids ro'yxat bo'lishi kerak")
    return db.set_control_test_courses(test_id, course_ids)


@router.get("/users/search")
def admin_search_users(q: str = "", admin=Depends(require_admin)):
    return {"users": db.search_users(q)}


@router.get("/control-tests/{test_id}/results")
def admin_control_test_results(test_id: int, admin=Depends(require_admin)):
    test = db.get_test(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test topilmadi")
    return {"results": db.get_control_test_results(test_id)}
