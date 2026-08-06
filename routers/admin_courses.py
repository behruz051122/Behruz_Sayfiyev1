# routers/admin_courses.py
from fastapi import APIRouter, Depends, Body

from routers.deps import require_admin
import database as db

router = APIRouter(prefix="/api/admin", tags=["admin-courses"])


# ---------- Kurslar ----------

@router.get("/courses")
def admin_list_courses(admin=Depends(require_admin)):
    courses = db.get_all_courses(only_active=False)
    for c in courses:
        c["lessons_count"] = db.count_course_lessons(c["id"])
    return {"courses": courses}


@router.post("/courses")
def admin_create_course(data: dict = Body(...), admin=Depends(require_admin)):
    return {"id": db.create_course(data)}


@router.put("/courses/{course_id}")
def admin_update_course(course_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    db.update_course(course_id, data)
    return {"ok": True}


@router.delete("/courses/{course_id}")
def admin_delete_course(course_id: int, admin=Depends(require_admin)):
    db.delete_course(course_id)
    return {"ok": True}


# ---------- Narx paketlari ----------

@router.get("/courses/{course_id}/pricing-tiers")
def admin_list_pricing_tiers(course_id: int, admin=Depends(require_admin)):
    return {"tiers": db.get_pricing_tiers(course_id, only_active=False)}


@router.post("/pricing-tiers")
def admin_create_pricing_tier(data: dict = Body(...), admin=Depends(require_admin)):
    return {"id": db.create_pricing_tier(data)}


@router.put("/pricing-tiers/{tier_id}")
def admin_update_pricing_tier(tier_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    db.update_pricing_tier(tier_id, data)
    return {"ok": True}


@router.delete("/pricing-tiers/{tier_id}")
def admin_delete_pricing_tier(tier_id: int, admin=Depends(require_admin)):
    db.delete_pricing_tier(tier_id)
    return {"ok": True}


# ---------- Bo'limlar (paragraflar) ----------

@router.get("/courses/{course_id}/paragraphs")
def admin_list_paragraphs(course_id: int, admin=Depends(require_admin)):
    paragraphs = db.get_paragraphs(course_id)
    for p in paragraphs:
        p["lessons_count"] = db.count_paragraph_lessons(p["id"])
    return {"paragraphs": paragraphs}


@router.post("/paragraphs")
def admin_create_paragraph(data: dict = Body(...), admin=Depends(require_admin)):
    return {"id": db.create_paragraph(data)}


@router.put("/paragraphs/{paragraph_id}")
def admin_update_paragraph(paragraph_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    db.update_paragraph(paragraph_id, data)
    return {"ok": True}


@router.delete("/paragraphs/{paragraph_id}")
def admin_delete_paragraph(paragraph_id: int, admin=Depends(require_admin)):
    db.delete_paragraph(paragraph_id)
    return {"ok": True}


# ---------- Darslar ----------

@router.get("/paragraphs/{paragraph_id}/lessons")
def admin_list_lessons(paragraph_id: int, admin=Depends(require_admin)):
    return {"lessons": db.get_lessons(paragraph_id)}


@router.post("/lessons")
def admin_create_lesson(data: dict = Body(...), admin=Depends(require_admin)):
    return {"id": db.create_lesson(data)}


@router.put("/lessons/{lesson_id}")
def admin_update_lesson(lesson_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    db.update_lesson(lesson_id, data)
    return {"ok": True}


@router.delete("/lessons/{lesson_id}")
def admin_delete_lesson(lesson_id: int, admin=Depends(require_admin)):
    db.delete_lesson(lesson_id)
    return {"ok": True}


# ---------- Obuna (qo'lda berish / uzaytirish) ----------

@router.post("/enroll")
def admin_grant_enrollment(data: dict = Body(...), admin=Depends(require_admin)):
    target_telegram_id = int(data["telegram_id"])
    course_id = int(data["course_id"])
    duration_days = data.get("duration_days")
    duration_days = int(duration_days) if duration_days else None
    db.grant_enrollment(target_telegram_id, course_id, duration_days)
    return {"ok": True}
