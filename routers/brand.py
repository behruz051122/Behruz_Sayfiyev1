# routers/brand.py
from fastapi import APIRouter

from config import BOT_USERNAME, BRAND_NAME, BRAND_SUB, ADMIN_CONTACT_USERNAME

router = APIRouter(prefix="/api", tags=["brand"])


@router.get("/brand")
def api_brand():
    return {
        "brand_name": BRAND_NAME,
        "brand_sub": BRAND_SUB,
        "bot_username": BOT_USERNAME,
        "admin_contact": ADMIN_CONTACT_USERNAME,
    }
