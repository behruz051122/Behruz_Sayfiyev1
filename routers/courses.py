# routers/courses.py
from fastapi import APIRouter, Depends, HTTPException

from routers.deps import get_verified_telegram_user
import database as db

router = APIRouter(prefix="/api", tags=["courses"])


@router.get("/courses")
def api_get_courses(resource_type: str = None, user=Depends(get_verified_telegram_user)):
    courses = db.get_all_courses(resource_type=resource_type)
    result = []
    for c in courses:
        access = db.compute_course_access(user["telegram_id"], c)
        c.update(access)
        c["lessons_count"] = db.count_course_lessons(c["id"])
        result.append(c)
    return {"courses": result}


@router.get("/course/{course_id}")
def api_get_course(course_id: int, user=Depends(get_verified_telegram_user)):
    course = db.get_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Kurs topilmadi")

    telegram_id = user["telegram_id"]
    access = db.compute_course_access(telegram_id, course)
    course.update(access)

    paragraphs = db.get_paragraphs(course_id)
    watched_ids = set(db.get_watched_lesson_ids(telegram_id, course_id)) if course["unlocked"] else set()

    for p in paragraphs:
        lessons = db.get_lessons(p["id"]) if course["unlocked"] else []
        for l in lessons:
            l["watched"] = l["id"] in watched_ids
        p["lessons"] = lessons
        p["lessons_count"] = db.count_paragraph_lessons(p["id"])

    course["paragraphs"] = paragraphs
    return course


@router.post("/lesson/{lesson_id}/watched")
def api_mark_watched(lesson_id: int, user=Depends(get_verified_telegram_user)):
    telegram_id = user["telegram_id"]
    db.get_or_create_user(telegram_id, user["first_name"], user.get("username"))
    awarded = db.mark_lesson_watched(telegram_id, lesson_id)
    db_user = db.get_or_create_user(telegram_id, user["first_name"], user.get("username"))
    return {"coin_awarded": awarded, "total_coins": db_user["coins"]}
