# routers/admin_bookshop.py
# Kitoblar do'koni (bosma kitoblar) mahsulotlarini ADMIN panelidan
# qo'shish/tahrirlash/o'chirish uchun.

from fastapi import APIRouter, Depends, Body

from routers.deps import require_admin
import database as db

router = APIRouter(prefix="/api/admin", tags=["admin-bookshop"])


@router.get("/book-products")
def admin_list_book_products(admin=Depends(require_admin)):
    return {"products": db.get_book_products(only_active=False)}


@router.post("/book-products")
def admin_create_book_product(data: dict = Body(...), admin=Depends(require_admin)):
    return {"id": db.create_book_product(data)}


@router.put("/book-products/{product_id}")
def admin_update_book_product(product_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    db.update_book_product(product_id, data)
    return {"ok": True}


@router.delete("/book-products/{product_id}")
def admin_delete_book_product(product_id: int, admin=Depends(require_admin)):
    db.delete_book_product(product_id)
    return {"ok": True}
