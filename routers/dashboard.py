# routers/dashboard.py
# Bosh sahifadagi 6 ta katakli menyu kartalarini (Kurslar, Testlar, Reyting,
# Kitoblar, O'yinlar, Natijalar) O'QISH uchun OCHIQ (autentifikatsiyasiz)
# endpoint. Tahrirlash faqat admin panelidan (routers/admin_dashboard.py).

from fastapi import APIRouter

import database as db

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard-cards")
def api_dashboard_cards():
    return {"cards": db.get_dashboard_cards(only_active=True)}
