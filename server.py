# server.py — API va admin panel backend (v3 — xavfsizlashtirilgan)
#
# XAVFSIZLIK O'ZGARISHLARI (v2 -> v3):
# 1. Endi telegram_id klientdan ochiq query-parametr sifatida ISHONCH BILAN
#    qabul qilinmaydi. Har bir so'rovda "X-Telegram-Init-Data" headeri orqali
#    Telegram imzolagan initData yuboriladi va server uni HMAC bilan tekshiradi
#    (auth.py). Faqat shundan keyin haqiqiy telegram_id aniqlanadi.
# 2. Admin panel endi ikkita yo'l bilan ishlaydi:
#      a) Oldindan ro'yxatdagi (ADMIN_TELEGRAM_IDS) Telegram foydalanuvchilari —
#         initData tasdiqlangach avtomatik admin (parolsiz, lekin soxtalashtirib
#         bo'lmaydi).
#      b) Parol orqali kirish — endi bcrypt xesh bilan solishtiriladi va
#         muvaffaqiyatli bo'lsa 12 soatlik JWT sessiya tokeni beriladi (parol
#         har safar qayta yuborilmaydi). Login urinishlari rate-limit qilingan.

from fastapi import FastAPI, Query, Header, HTTPException, Body, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import os

from config import (
    ADMIN_PASSWORD_HASH, ADMIN_TELEGRAM_IDS, ADMIN_CONTACT_USERNAME,
    BOT_USERNAME, BRAND_NAME, BRAND_SUB, BOT_TOKEN, JWT_SECRET_KEY,
)
import database as db
import auth as auth_module

app = FastAPI()

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    db.init_db()
    db.add_sample_courses()


# ---------- AUTENTIFIKATSIYA DEPENDENCY'LARI ----------

def get_verified_telegram_user(x_telegram_init_data: str = Header(default="")) -> dict:
    """
    Har bir 'himoyalangan' foydalanuvchi endpointi shu orqali chaqiruvchining
    HAQIQIY Telegram identifikatorini oladi. initData Telegram tomonidan bot
    tokeni bilan imzolangani uchun buni soxtalashtirib bo'lmaydi.
    """
    try:
        return auth_module.parse_and_verify_init_data(x_telegram_init_data, BOT_TOKEN)
    except auth_module.TelegramAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))


def require_admin(
    authorization: str = Header(default=""),
    x_telegram_init_data: str = Header(default=""),
) -> dict:
    """
    Admin endpointlari uchun. Ikki usuldan BIRI orqali o'tadi:
      1) Authorization: Bearer <JWT> — parol orqali login qilingan sessiya
      2) X-Telegram-Init-Data — tasdiqlangan telegram_id ADMIN_TELEGRAM_IDS
         ro'yxatida bo'lsa
    """
    if authorization.startswith("Bearer "):
        token = authorization[7:]
        payload = auth_module.verify_admin_session_token(token, JWT_SECRET_KEY)
        if payload:
            return {"method": "password_session"}

    if x_telegram_init_data:
        try:
            data = auth_module.parse_and_verify_init_data(x_telegram_init_data, BOT_TOKEN)
            if data["telegram_id"] in ADMIN_TELEGRAM_IDS:
                return {"method": "telegram_whitelist", "telegram_id": data["telegram_id"]}
        except auth_module.TelegramAuthError:
            pass

    raise HTTPException(status_code=401, detail="Admin huquqi tasdiqlanmadi")


# ---------- PUBLIC: brand ----------

@app.get("/api/brand")
def api_brand():
    return {"brand_name": BRAND_NAME, "brand_sub": BRAND_SUB, "bot_username": BOT_USERNAME, "admin_contact": ADMIN_CONTACT_USERNAME}


@app.get("/api/debug/db-info")
def api_debug_db_info(admin=Depends(require_admin)):
    """Diagnostika endpointi — endi faqat admin ko'ra oladi (avval ochiq edi)."""
    path = db.DB_PATH
    exists = os.path.exists(path)
    size = os.path.getsize(path) if exists else 0
    is_persistent_path = path.startswith("/data")
    course_count = len(db.get_all_courses(only_active=False))
    return {
        "db_path": path,
        "file_exists": exists,
        "file_size_bytes": size,
        "looks_persistent": is_persistent_path,
        "courses_in_database": course_count,
        "railway_db_path_env_set": os.environ.get("DB_PATH") is not None,
    }


# ---------- PUBLIC: user (endi tasdiqlangan identifikatsiya bilan) ----------

@app.get("/api/user")
def api_get_user(user=Depends(get_verified_telegram_user)):
    db_user = db.get_or_create_user(
        telegram_id=user["telegram_id"],
        first_name=user["first_name"],
        username=user.get("username"),
    )
    db_user["confirmed_referrals"] = db.get_confirmed_referral_count(user["telegram_id"])
    db_user["rank"] = db.get_user_rank(user["telegram_id"])
    return db_user


@app.get("/api/is-admin")
def api_is_admin(user=Depends(get_verified_telegram_user)):
    return {"is_admin": user["telegram_id"] in ADMIN_TELEGRAM_IDS}


@app.get("/api/referral-link")
def api_referral_link(user=Depends(get_verified_telegram_user)):
    telegram_id = user["telegram_id"]
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{telegram_id}"
    return {
        "link": link,
        "confirmed_referrals": db.get_confirmed_referral_count(telegram_id),
        "referrals": db.get_referral_progress(telegram_id)
    }


@app.get("/api/leaderboard")
def api_leaderboard(user=Depends(get_verified_telegram_user)):
    return {
        "leaderboard": db.get_leaderboard(100),
        "my_rank": db.get_user_rank(user["telegram_id"])
    }


@app.get("/api/my-enrollments")
def api_my_enrollments(user=Depends(get_verified_telegram_user)):
    return {"enrollments": db.get_user_enrollments(user["telegram_id"])}


# ---------- PUBLIC: courses / paragraphs / lessons ----------

@app.get("/api/courses")
def api_get_courses(resource_type: str = None, user=Depends(get_verified_telegram_user)):
    courses = db.get_all_courses(resource_type=resource_type)
    result = []
    for c in courses:
        access = db.compute_course_access(user["telegram_id"], c)
        c.update(access)
        c["lessons_count"] = db.count_course_lessons(c["id"])
        result.append(c)
    return {"courses": result}


@app.get("/api/course/{course_id}")
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


@app.post("/api/lesson/{lesson_id}/watched")
def api_mark_watched(lesson_id: int, user=Depends(get_verified_telegram_user)):
    telegram_id = user["telegram_id"]
    db.get_or_create_user(telegram_id, user["first_name"], user.get("username"))
    awarded = db.mark_lesson_watched(telegram_id, lesson_id)
    db_user = db.get_or_create_user(telegram_id, user["first_name"], user.get("username"))
    return {"coin_awarded": awarded, "total_coins": db_user["coins"]}


# ---------- ADMIN: parol orqali login (JWT sessiya beradi) ----------

@app.post("/api/admin/login")
@limiter.limit("5/15minutes")
def admin_login(request: Request, password: str = Body(..., embed=True)):
    if not auth_module.verify_password(password, ADMIN_PASSWORD_HASH):
        raise HTTPException(status_code=401, detail="Noto'g'ri parol")
    token = auth_module.create_admin_session_token(JWT_SECRET_KEY)
    return {"token": token, "expires_in_seconds": auth_module.ADMIN_TOKEN_TTL_SECONDS}


# ---------- ADMIN: courses CRUD ----------

@app.get("/api/admin/courses")
def admin_list_courses(admin=Depends(require_admin)):
    courses = db.get_all_courses(only_active=False)
    for c in courses:
        c["lessons_count"] = db.count_course_lessons(c["id"])
    return {"courses": courses}


@app.post("/api/admin/courses")
def admin_create_course(data: dict = Body(...), admin=Depends(require_admin)):
    return {"id": db.create_course(data)}


@app.put("/api/admin/courses/{course_id}")
def admin_update_course(course_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    db.update_course(course_id, data)
    return {"ok": True}


@app.delete("/api/admin/courses/{course_id}")
def admin_delete_course(course_id: int, admin=Depends(require_admin)):
    db.delete_course(course_id)
    return {"ok": True}


# ---------- ADMIN: paragraphs CRUD ----------

@app.get("/api/admin/courses/{course_id}/paragraphs")
def admin_list_paragraphs(course_id: int, admin=Depends(require_admin)):
    paragraphs = db.get_paragraphs(course_id)
    for p in paragraphs:
        p["lessons_count"] = db.count_paragraph_lessons(p["id"])
    return {"paragraphs": paragraphs}


@app.post("/api/admin/paragraphs")
def admin_create_paragraph(data: dict = Body(...), admin=Depends(require_admin)):
    return {"id": db.create_paragraph(data)}


@app.put("/api/admin/paragraphs/{paragraph_id}")
def admin_update_paragraph(paragraph_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    db.update_paragraph(paragraph_id, data)
    return {"ok": True}


@app.delete("/api/admin/paragraphs/{paragraph_id}")
def admin_delete_paragraph(paragraph_id: int, admin=Depends(require_admin)):
    db.delete_paragraph(paragraph_id)
    return {"ok": True}


# ---------- ADMIN: lessons CRUD ----------

@app.get("/api/admin/paragraphs/{paragraph_id}/lessons")
def admin_list_lessons(paragraph_id: int, admin=Depends(require_admin)):
    return {"lessons": db.get_lessons(paragraph_id)}


@app.post("/api/admin/lessons")
def admin_create_lesson(data: dict = Body(...), admin=Depends(require_admin)):
    return {"id": db.create_lesson(data)}


@app.put("/api/admin/lessons/{lesson_id}")
def admin_update_lesson(lesson_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    db.update_lesson(lesson_id, data)
    return {"ok": True}


@app.delete("/api/admin/lessons/{lesson_id}")
def admin_delete_lesson(lesson_id: int, admin=Depends(require_admin)):
    db.delete_lesson(lesson_id)
    return {"ok": True}


# ---------- ADMIN: enrollments (qo'lda obuna berish / uzaytirish) ----------

@app.post("/api/admin/enroll")
def admin_grant_enrollment(data: dict = Body(...), admin=Depends(require_admin)):
    target_telegram_id = int(data["telegram_id"])
    course_id = int(data["course_id"])
    duration_days = data.get("duration_days")
    duration_days = int(duration_days) if duration_days else None
    db.grant_enrollment(target_telegram_id, course_id, duration_days)
    return {"ok": True}


# ---------- PUBLIC: testlar ----------

@app.get("/api/tests")
def api_get_tests(subject: str = None, user=Depends(get_verified_telegram_user)):
    tests = db.get_all_tests(subject=subject)
    for t in tests:
        t["question_count"] = db.count_test_questions(t["id"])
    return {"tests": tests}


@app.get("/api/test/{test_id}")
def api_get_test(test_id: int, user=Depends(get_verified_telegram_user)):
    test = db.get_test(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test topilmadi")
    questions = db.get_questions(test_id)
    safe_questions = []
    for q in questions:
        safe_questions.append({
            "id": q["id"], "question_text": q["question_text"], "image_url": q["image_url"],
            "option_1": q["option_1"], "option_2": q["option_2"],
            "option_3": q["option_3"], "option_4": q["option_4"], "order_num": q["order_num"]
        })
    test["questions"] = safe_questions
    return test


@app.post("/api/test/{test_id}/start")
def api_start_test(test_id: int, user=Depends(get_verified_telegram_user)):
    telegram_id = user["telegram_id"]
    db.get_or_create_user(telegram_id, user["first_name"], user.get("username"))
    attempt_id = db.start_attempt(telegram_id, test_id)
    return {"attempt_id": attempt_id}


def _get_owned_attempt_or_403(attempt_id: int, telegram_id: int) -> dict:
    """Bu urinish (attempt) haqiqatan ham so'rov yuborayotgan foydalanuvchiga
    tegishli ekanligini tekshiradi — aks holda birov boshqa birovning testiga
    "javob qo'shib qo'yishi" mumkin edi."""
    attempt = db.get_attempt(attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Urinish topilmadi")
    if attempt["telegram_id"] != telegram_id:
        raise HTTPException(status_code=403, detail="Bu urinish sizga tegishli emas")
    return attempt


@app.post("/api/attempt/{attempt_id}/answer")
def api_submit_answer(attempt_id: int, data: dict = Body(...), user=Depends(get_verified_telegram_user)):
    telegram_id = user["telegram_id"]
    _get_owned_attempt_or_403(attempt_id, telegram_id)
    question_id = int(data["question_id"])
    selected_index = int(data["selected_index"])
    db.get_or_create_user(telegram_id, user["first_name"], user.get("username"))
    result = db.submit_answer(telegram_id, attempt_id, question_id, selected_index)
    return result


@app.post("/api/attempt/{attempt_id}/finish")
def api_finish_attempt(attempt_id: int, user=Depends(get_verified_telegram_user)):
    _get_owned_attempt_or_403(attempt_id, user["telegram_id"])
    result = db.finish_attempt(attempt_id)
    if not result:
        raise HTTPException(status_code=404, detail="Urinish topilmadi")
    return result


@app.get("/api/my-test-results")
def api_my_test_results(user=Depends(get_verified_telegram_user)):
    return {"results": db.get_user_test_results(user["telegram_id"])}


# ---------- ADMIN: testlar CRUD ----------

@app.get("/api/admin/tests")
def admin_list_tests(admin=Depends(require_admin)):
    tests = db.get_all_tests(only_active=False)
    for t in tests:
        t["question_count"] = db.count_test_questions(t["id"])
    return {"tests": tests}


@app.post("/api/admin/tests")
def admin_create_test(data: dict = Body(...), admin=Depends(require_admin)):
    return {"id": db.create_test(data)}


@app.put("/api/admin/tests/{test_id}")
def admin_update_test(test_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    db.update_test(test_id, data)
    return {"ok": True}


@app.delete("/api/admin/tests/{test_id}")
def admin_delete_test(test_id: int, admin=Depends(require_admin)):
    db.delete_test(test_id)
    return {"ok": True}


@app.get("/api/admin/tests/{test_id}/questions")
def admin_list_questions(test_id: int, admin=Depends(require_admin)):
    return {"questions": db.get_questions(test_id)}


@app.post("/api/admin/questions")
def admin_create_question(data: dict = Body(...), admin=Depends(require_admin)):
    return {"id": db.create_question(data)}


@app.put("/api/admin/questions/{question_id}")
def admin_update_question(question_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    db.update_question(question_id, data)
    return {"ok": True}


@app.delete("/api/admin/questions/{question_id}")
def admin_delete_question(question_id: int, admin=Depends(require_admin)):
    db.delete_question(question_id)
    return {"ok": True}


# Mini App va admin panel statik fayllari
app.mount("/", StaticFiles(directory="webapp", html=True), name="webapp")
