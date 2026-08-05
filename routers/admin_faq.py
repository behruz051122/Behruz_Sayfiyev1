# routers/admin_faq.py
# FAQ / Yordam bo'limidagi savol-javoblarni ADMIN panelidan
# qo'shish/tahrirlash/o'chirish uchun.

from fastapi import APIRouter, Depends, Body

from routers.deps import require_admin
import database as db

router = APIRouter(prefix="/api/admin", tags=["admin-faq"])


@router.get("/faq")
def admin_list_faq_items(admin=Depends(require_admin)):
    return {"items": db.get_faq_items(only_active=False)}


@router.post("/faq")
def admin_create_faq_item(data: dict = Body(...), admin=Depends(require_admin)):
    return {"id": db.create_faq_item(data)}


@router.put("/faq/{faq_id}")
def admin_update_faq_item(faq_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    db.update_faq_item(faq_id, data)
    return {"ok": True}


@router.delete("/faq/{faq_id}")
def admin_delete_faq_item(faq_id: int, admin=Depends(require_admin)):
    db.delete_faq_item(faq_id)
    return {"ok": True}
