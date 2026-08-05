# routers/bookshop.py
# Kitoblar do'koni (bosma kitoblar) — talabalar tomonidan O'QISH uchun ochiq
# (autentifikatsiyasiz) endpoint. Mahsulot qo'shish/tahrirlash faqat admin
# panelidan (routers/admin_bookshop.py).

from fastapi import APIRouter

import database as db

router = APIRouter(prefix="/api", tags=["bookshop"])


@router.get("/book-products")
def api_book_products(category: str = None):
    return {"products": db.get_book_products(category=category, only_active=True)}
