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


@router.get("/users/search")
def admin_search_users(q: str = "", admin=Depends(require_admin)):
    return {"users": db.search_users(q)}
