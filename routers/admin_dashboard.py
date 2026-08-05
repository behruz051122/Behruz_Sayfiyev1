# routers/admin_dashboard.py
# Bosh sahifadagi 6 ta katakli menyu kartasining sarlavha/teg/belgi/faollik
# qiymatlarini ADMIN panelidan tahrirlash uchun.

from fastapi import APIRouter, Depends, Body

from routers.deps import require_admin
import database as db

router = APIRouter(prefix="/api/admin", tags=["admin-dashboard"])


@router.get("/dashboard-cards")
def admin_list_dashboard_cards(admin=Depends(require_admin)):
    return {"cards": db.get_dashboard_cards(only_active=False)}


@router.put("/dashboard-cards/{card_key}")
def admin_update_dashboard_card(card_key: str, data: dict = Body(...), admin=Depends(require_admin)):
    db.update_dashboard_card(card_key, data)
    return {"ok": True}
