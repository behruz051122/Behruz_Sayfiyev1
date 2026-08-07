# routers/courses.py
from fastapi import APIRouter, Depends, HTTPException

from routers.deps import get_verified_telegram_user
import database as db
import access_control


async def _member_groups(telegram_id: int):
    """O'quvchi a'zo bo'lgan pullik guruhlar (keshdan, kerak bo'lsa yangilab).

    Bu yerda `await` qilinishining sababi: kesh eskirgan bo'lsa Telegram'dan
    haqiqiy holatni so'raymiz. Kesh yangi bo'lsa — hech qanday tarmoq
    so'rovi bo'lmaydi, shuning uchun ilova sekinlashmaydi.
    """
    if not db.get_access_groups(only_active=True):
        return set()          # guruh sozlanmagan — bu tizim umuman ishlamaydi
    try:
        import bot as bot_module
        return await access_control.refresh_user_memberships(bot_module.bot, telegram_id)
    except Exception:
        # Telegram javob bermasa — keshdagi oxirgi ma'lum holat bilan davom etamiz
        return db.get_member_group_ids(telegram_id)

router = APIRouter(prefix="/api", tags=["courses"])


@router.get("/course-categories")
def api_get_course_categories():
    return {"categories": db.get_course_categories(only_active=True)}


@router.get("/courses")
async def api_get_courses(resource_type: str = None, user=Depends(get_verified_telegram_user)):
    courses = db.get_all_courses(resource_type=resource_type)
    category_map = db.get_category_ids_for_courses([c["id"] for c in courses])
    member_groups = await _member_groups(user["telegram_id"])
    result = []
    for c in courses:
        access = db.compute_course_access(user["telegram_id"], c, member_groups)
        c.update(access)
        real_lessons_count = db.count_course_lessons(c["id"])
        c["lessons_count"] = c.get("lessons_count_override") or real_lessons_count
        c["free_lessons_count"] = db.count_free_preview_lessons(c["id"])
        c["category_ids"] = category_map.get(c["id"], [])
        result.append(c)
    return {"courses": result}


@router.get("/course/{course_id}")
async def api_get_course(course_id: int, user=Depends(get_verified_telegram_user)):
    course = db.get_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Kurs topilmadi")

    telegram_id = user["telegram_id"]
    member_groups = await _member_groups(telegram_id)
    access = db.compute_course_access(telegram_id, course, member_groups)
    course.update(access)
    course["pricing_tiers"] = db.get_pricing_tiers(course_id)
    course["categories"] = db.get_categories_for_course(course_id)

    paragraphs = db.get_paragraphs(course_id)
    watched_ids = set(db.get_watched_lesson_ids(telegram_id, course_id)) if course["unlocked"] else set()
    # Kurs qulflangan bo'lsa ham, admin "bepul namuna" deb belgilagan darslar
    # ro'yxatdan o'tmasdan ko'rsatiladi (Kelajakmediklari_bot'dagi "N BEPUL"
    # belgisi shu ma'noni bildiradi — reklama/namuna sifatida ochiq turadi).
    # QOLGAN (qulflangan) darslar endi BUTUNLAY yashirilmaydi — talaba
    # "yo'lak" ko'rinishida ularning NOMI/tartibini ko'radi (Kelajakmediklari
    # bot'dagi kabi, qulf belgisi bilan), faqat video/tavsif kabi haqiqiy
    # kontent berilmaydi.
    free_preview_ids = set() if course["unlocked"] else db.get_free_preview_lesson_ids(course_id)

    for p in paragraphs:
        raw_lessons = db.get_lessons(p["id"])
        lessons = []
        for l in raw_lessons:
            is_preview = bool(l.get("is_free_preview"))
            if course["unlocked"] or is_preview:
                lessons.append({
                    **l,
                    "watched": l["id"] in watched_ids,
                    "is_free_preview": is_preview,
                    "locked": False,
                })
            else:
                lessons.append({
                    "id": l["id"], "title": l["title"], "order_num": l["order_num"],
                    "is_free_preview": False, "locked": True, "watched": False,
                    "video_url": None, "image_url": None, "description": None, "table_data": None,
                })
        p["lessons"] = lessons
        p["lessons_count"] = db.count_paragraph_lessons(p["id"])

    real_lessons_count = db.count_course_lessons(course_id)
    course["lessons_count"] = course.get("lessons_count_override") or real_lessons_count
    course["paragraphs"] = paragraphs
    return course


@router.post("/lesson/{lesson_id}/watched")
def api_mark_watched(lesson_id: int, user=Depends(get_verified_telegram_user)):
    telegram_id = user["telegram_id"]
    db.get_or_create_user(telegram_id, user["first_name"], user.get("username"))
    awarded = db.mark_lesson_watched(telegram_id, lesson_id)
    db_user = db.get_or_create_user(telegram_id, user["first_name"], user.get("username"))
    return {"coin_awarded": awarded, "total_coins": db_user["coins"]}


@router.post("/access/refresh")
async def api_refresh_access(user=Depends(get_verified_telegram_user)):
    """A'zolikni DARHOL qayta tekshiradi.

    O'quvchi "Men qo'shildim" tugmasini bosganda chaqiriladi. Keshni
    chetlab o'tib (force=True) Telegram'dan haqiqiy holatni so'raydi —
    shunda o'quvchi 10 daqiqa kutib o'tirmaydi.
    """
    telegram_id = user["telegram_id"]
    if not db.get_access_groups(only_active=True):
        return {"success": True, "member_group_ids": [], "configured": False}

    try:
        import bot as bot_module
        ids = await access_control.refresh_user_memberships(
            bot_module.bot, telegram_id, force=True)
    except Exception:
        ids = db.get_member_group_ids(telegram_id)

    return {"success": True, "member_group_ids": sorted(ids), "configured": True}
