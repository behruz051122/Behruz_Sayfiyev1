# server.py — API va admin panel backend (v2)

from fastapi import FastAPI, Query, Header, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from config import ADMIN_PASSWORD, ADMIN_TELEGRAM_IDS, ADMIN_CONTACT_USERNAME, BOT_USERNAME, BRAND_NAME, BRAND_SUB
import database as db

app = FastAPI()

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


def check_admin(x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
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
    return {"brand_name": BRAND_NAME, "brand_sub": BRAND_SUB, "bot_username": BOT_USERNAME, "admin_contact": ADMIN_CONTACT_USERNAME}


@app.get("/api/user")
def api_get_user(telegram_id: int = Query(...), first_name: str = Query("Foydalanuvchi")):
    user = db.get_or_create_user(telegram_id=telegram_id, first_name=first_name)
    user["confirmed_referrals"] = db.get_confirmed_referral_count(telegram_id)
    user["rank"] = db.get_user_rank(telegram_id)
    return user


@app.get("/api/is-admin")
def api_is_admin(telegram_id: int = Query(...)):
    return {"is_admin": telegram_id in ADMIN_TELEGRAM_IDS}


@app.get("/api/referral-link")
def api_referral_link(telegram_id: int = Query(...)):
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{telegram_id}"
    return {
        "link": link,
        "confirmed_referrals": db.get_confirmed_referral_count(telegram_id),
        "referrals": db.get_referral_progress(telegram_id)
    }


@app.get("/api/leaderboard")
def api_leaderboard(telegram_id: int = Query(...)):
    return {
        "leaderboard": db.get_leaderboard(100),
        "my_rank": db.get_user_rank(telegram_id)
    }


@app.get("/api/my-enrollments")
def api_my_enrollments(telegram_id: int = Query(...)):
    return {"enrollments": db.get_user_enrollments(telegram_id)}


# ---------- PUBLIC: courses / paragraphs / lessons ----------

@app.get("/api/courses")
def api_get_courses(resource_type: str = None, telegram_id: int = Query(...)):
    courses = db.get_all_courses(resource_type=resource_type)
    result = []
    for c in courses:
        access = db.compute_course_access(telegram_id, c)
        c.update(access)
        c["lessons_count"] = db.count_course_lessons(c["id"])
        result.append(c)
    return {"courses": result}


@app.get("/api/course/{course_id}")
def api_get_course(course_id: int, telegram_id: int = Query(...)):
    course = db.get_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Kurs topilmadi")

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
def api_mark_watched(lesson_id: int, telegram_id: int = Body(..., embed=True)):
    db.get_or_create_user(telegram_id, "Foydalanuvchi")  # coin berilishidan oldin foydalanuvchi mavjudligini ta'minlaymiz
    awarded = db.mark_lesson_watched(telegram_id, lesson_id)
    user = db.get_or_create_user(telegram_id, "Foydalanuvchi")
    return {"coin_awarded": awarded, "total_coins": user["coins"]}


# ---------- ADMIN: auth ----------

@app.post("/api/admin/login")
def admin_login(password: str = Body(..., embed=True)):
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Noto'g'ri parol")
    return {"ok": True}


# ---------- ADMIN: courses CRUD ----------

@app.get("/api/admin/courses")
def admin_list_courses(x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    courses = db.get_all_courses(only_active=False)
    for c in courses:
        c["lessons_count"] = db.count_course_lessons(c["id"])
    return {"courses": courses}


@app.post("/api/admin/courses")
def admin_create_course(data: dict = Body(...), x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    return {"id": db.create_course(data)}


@app.put("/api/admin/courses/{course_id}")
def admin_update_course(course_id: int, data: dict = Body(...), x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    db.update_course(course_id, data)
    return {"ok": True}


@app.delete("/api/admin/courses/{course_id}")
def admin_delete_course(course_id: int, x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    db.delete_course(course_id)
    return {"ok": True}


# ---------- ADMIN: paragraphs CRUD ----------

@app.get("/api/admin/courses/{course_id}/paragraphs")
def admin_list_paragraphs(course_id: int, x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    paragraphs = db.get_paragraphs(course_id)
    for p in paragraphs:
        p["lessons_count"] = db.count_paragraph_lessons(p["id"])
    return {"paragraphs": paragraphs}


@app.post("/api/admin/paragraphs")
def admin_create_paragraph(data: dict = Body(...), x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    return {"id": db.create_paragraph(data)}


@app.put("/api/admin/paragraphs/{paragraph_id}")
def admin_update_paragraph(paragraph_id: int, data: dict = Body(...), x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    db.update_paragraph(paragraph_id, data)
    return {"ok": True}


@app.delete("/api/admin/paragraphs/{paragraph_id}")
def admin_delete_paragraph(paragraph_id: int, x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    db.delete_paragraph(paragraph_id)
    return {"ok": True}


# ---------- ADMIN: lessons CRUD ----------

@app.get("/api/admin/paragraphs/{paragraph_id}/lessons")
def admin_list_lessons(paragraph_id: int, x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    return {"lessons": db.get_lessons(paragraph_id)}


@app.post("/api/admin/lessons")
def admin_create_lesson(data: dict = Body(...), x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    return {"id": db.create_lesson(data)}


@app.put("/api/admin/lessons/{lesson_id}")
def admin_update_lesson(lesson_id: int, data: dict = Body(...), x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    db.update_lesson(lesson_id, data)
    return {"ok": True}


@app.delete("/api/admin/lessons/{lesson_id}")
def admin_delete_lesson(lesson_id: int, x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    db.delete_lesson(lesson_id)
    return {"ok": True}


# ---------- ADMIN: enrollments (qo'lda obuna berish / uzaytirish) ----------

@app.post("/api/admin/enroll")
def admin_grant_enrollment(data: dict = Body(...), x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    target_telegram_id = int(data["telegram_id"])
    course_id = int(data["course_id"])
    duration_days = data.get("duration_days")
    duration_days = int(duration_days) if duration_days else None
    db.grant_enrollment(target_telegram_id, course_id, duration_days)
    return {"ok": True}


# ---------- PUBLIC: testlar ----------

@app.get("/api/tests")
def api_get_tests(subject: str = None, telegram_id: int = Query(...)):
    tests = db.get_all_tests(subject=subject)
    for t in tests:
        t["question_count"] = db.count_test_questions(t["id"])
    return {"tests": tests}


@app.get("/api/test/{test_id}")
def api_get_test(test_id: int, telegram_id: int = Query(...)):
    test = db.get_test(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test topilmadi")
    questions = db.get_questions(test_id)
    # Foydalanuvchiga to'g'ri javob indeksini oldindan yubormaymiz — aldashning oldini olish uchun
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
def api_start_test(test_id: int, telegram_id: int = Body(..., embed=True)):
    db.get_or_create_user(telegram_id, "Foydalanuvchi")
    attempt_id = db.start_attempt(telegram_id, test_id)
    return {"attempt_id": attempt_id}


@app.post("/api/attempt/{attempt_id}/answer")
def api_submit_answer(attempt_id: int, data: dict = Body(...)):
    telegram_id = int(data["telegram_id"])
    question_id = int(data["question_id"])
    selected_index = int(data["selected_index"])
    db.get_or_create_user(telegram_id, "Foydalanuvchi")
    result = db.submit_answer(telegram_id, attempt_id, question_id, selected_index)
    return result


@app.post("/api/attempt/{attempt_id}/finish")
def api_finish_attempt(attempt_id: int):
    result = db.finish_attempt(attempt_id)
    if not result:
        raise HTTPException(status_code=404, detail="Urinish topilmadi")
    return result


@app.get("/api/my-test-results")
def api_my_test_results(telegram_id: int = Query(...)):
    return {"results": db.get_user_test_results(telegram_id)}


# ---------- ADMIN: testlar CRUD ----------

@app.get("/api/admin/tests")
def admin_list_tests(x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    tests = db.get_all_tests(only_active=False)
    for t in tests:
        t["question_count"] = db.count_test_questions(t["id"])
    return {"tests": tests}


@app.post("/api/admin/tests")
def admin_create_test(data: dict = Body(...), x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    return {"id": db.create_test(data)}


@app.put("/api/admin/tests/{test_id}")
def admin_update_test(test_id: int, data: dict = Body(...), x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    db.update_test(test_id, data)
    return {"ok": True}


@app.delete("/api/admin/tests/{test_id}")
def admin_delete_test(test_id: int, x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    db.delete_test(test_id)
    return {"ok": True}


@app.get("/api/admin/tests/{test_id}/questions")
def admin_list_questions(test_id: int, x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    return {"questions": db.get_questions(test_id)}


@app.post("/api/admin/questions")
def admin_create_question(data: dict = Body(...), x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    return {"id": db.create_question(data)}


@app.put("/api/admin/questions/{question_id}")
def admin_update_question(question_id: int, data: dict = Body(...), x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    db.update_question(question_id, data)
    return {"ok": True}


@app.delete("/api/admin/questions/{question_id}")
def admin_delete_question(question_id: int, x_admin_password: str = Header(default=""), x_telegram_id: str = Header(default="")):
    check_admin(x_admin_password, x_telegram_id)
    db.delete_question(question_id)
    return {"ok": True}


# Mini App va admin panel statik fayllari
app.mount("/", StaticFiles(directory="webapp", html=True), name="webapp")
