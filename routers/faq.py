# routers/faq.py
# FAQ / Yordam bo'limi — talabalar uchun O'QISH maqsadida ochiq
# (autentifikatsiyasiz) endpoint. Savol-javob qo'shish/tahrirlash faqat
# admin panelidan (routers/admin_faq.py).

from fastapi import APIRouter

import database as db

router = APIRouter(prefix="/api", tags=["faq"])


@router.get("/faq")
def api_faq_items():
    return {"items": db.get_faq_items(only_active=True)}
