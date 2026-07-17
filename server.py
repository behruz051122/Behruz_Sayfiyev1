# server.py
# Mini App uchun API va admin panel backend

from fastapi import FastAPI, Query, Header, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from config import ADMIN_PASSWORD, ADMIN_TELEGRAM_IDS, BOT_USERNAME, BRAND_NAME, BRAND_SUB
from database import (
    init_db, add_sample_courses, get_or_create_user,
    get_all_courses, get_course, create_course, update_course, delete_course,
    get_lessons, create_lesson, update_lesson, delete_lesson, get_lessons_count,
    get_confirmed_referral_count, get_referral_progress
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()
    add_sample_courses()


def check_admin(x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    """Admin ekanini ikki xil usulda tekshiradi:
    1) Mini App ichidan: X-Telegram-Id header orqali (ADMIN_TELEGRAM_IDS ro'yxati bilan solishtiriladi)
    2) Alohida admin.html sahifasidan: X-Admin-Password header orqali
    """
    if x_admin_password and x_admin_password == ADMIN_PASSWORD:
        return True
    if x_telegram_id:
        try:
            if int(x_telegram_id) in ADMIN_TELEGRAM_IDS:
                return True
        except ValueError:
            pass
    raise HTTPException(status_code=401, detail="Ruxsat yo'q")


# ---------- PUBLIC: brand / user ----------

@app.get("/api/brand")
def api_brand():
    return {"brand_name": BRAND_NAME, "brand_sub": BRAND_SUB}


@app.get("/api/user")
def api_get_user(telegram_id: int = Query(...), first_name: str = Query("Foydalanuvchi")):
    user = get_or_create_user(telegram_id=telegram_id, first_name=first_name)
    referrals = get_confirmed_referral_count(telegram_id)
    user["confirmed_referrals"] = referrals
    return user


@app.get("/api/is-admin")
def api_is_admin(telegram_id: int = Query(...)):
    return {"is_admin": telegram_id in ADMIN_TELEGRAM_IDS}


@app.get("/api/referral-link")
def api_referral_link(telegram_id: int = Query(...)):
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{telegram_id}"
    progress = get_referral_progress(telegram_id)
    confirmed = get_confirmed_referral_count(telegram_id)
    return {"link": link, "confirmed_referrals": confirmed, "referrals": progress}


# ---------- PUBLIC: courses / lessons ----------

@app.get("/api/courses")
def api_get_courses(resource_type: str = None, telegram_id: int = Query(...)):
    courses = get_all_courses(resource_type=resource_type)
    user_referrals = get_confirmed_referral_count(telegram_id)

    result = []
    for c in courses:
        unlocked = bool(c["is_free"]) or user_referrals >= c["required_referrals"]
        c["unlocked"] = unlocked
        c["user_referrals"] = user_referrals
        c["lessons_count"] = get_lessons_count(c["id"])
        result.append(c)
    return {"courses": result}


@app.get("/api/course/{course_id}")
def api_get_course(course_id: int, telegram_id: int = Query(...)):
    course = get_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Kurs topilmadi")

    user_referrals = get_confirmed_referral_count(telegram_id)
    unlocked = bool(course["is_free"]) or user_referrals >= course["required_referrals"]
    course["unlocked"] = unlocked
    course["user_referrals"] = user_referrals

    if unlocked:
        course["lessons"] = get_lessons(course_id)
    else:
        course["lessons"] = []

    return course


# ---------- ADMIN: auth (admin.html uchun, zaxira variant) ----------

@app.post("/api/admin/login")
def admin_login(password: str = Body(..., embed=True)):
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Noto'g'ri parol")
    return {"ok": True}


# ---------- ADMIN: courses CRUD ----------

@app.get("/api/admin/courses")
def admin_list_courses(x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    courses = get_all_courses(only_active=False)
    for c in courses:
        c["lessons_count"] = get_lessons_count(c["id"])
    return {"courses": courses}


@app.post("/api/admin/courses")
def admin_create_course(data: dict = Body(...), x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    new_id = create_course(data)
    return {"id": new_id}


@app.put("/api/admin/courses/{course_id}")
def admin_update_course(course_id: int, data: dict = Body(...), x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    update_course(course_id, data)
    return {"ok": True}


@app.delete("/api/admin/courses/{course_id}")
def admin_delete_course(course_id: int, x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    delete_course(course_id)
    return {"ok": True}


# ---------- ADMIN: lessons CRUD ----------

@app.get("/api/admin/courses/{course_id}/lessons")
def admin_list_lessons(course_id: int, x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    return {"lessons": get_lessons(course_id)}


@app.post("/api/admin/lessons")
def admin_create_lesson(data: dict = Body(...), x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    new_id = create_lesson(data)
    return {"id": new_id}


@app.put("/api/admin/lessons/{lesson_id}")
def admin_update_lesson(lesson_id: int, data: dict = Body(...), x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    update_lesson(lesson_id, data)
    return {"ok": True}


@app.delete("/api/admin/lessons/{lesson_id}")
def admin_delete_lesson(lesson_id: int, x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    delete_lesson(lesson_id)
    return {"ok": True}


# Mini App va admin panel statik fayllari
app.mount("/", StaticFiles(directory="webapp", html=True), name="webapp")
