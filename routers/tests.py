# routers/tests.py
from fastapi import APIRouter, Depends, HTTPException, Body

from routers.deps import get_verified_telegram_user
import database as db

router = APIRouter(prefix="/api", tags=["tests"])


def _ensure_control_test_access(test: dict, telegram_id: int):
    """Nazorat testiga faqat admin tomonidan BEVOSITA tayinlangan yoki
    bog'langan kursga yozilgan o'quvchilarga ruxsat berilishini serverning
    o'zida tekshiradi. Bu — frontend'dagi ro'yxat filtri buzilsa ham
    (masalan brauzer konsolidan to'g'ridan-to'g'ri so'rov yuborilsa ham)
    ishlaydigan haqiqiy himoya."""
    access = db.compute_control_test_access(telegram_id, test)
    if not access["unlocked"]:
        raise HTTPException(status_code=403, detail="Bu nazorat testi sizga hali ochilmagan — ustozingiz sizni ro'yxatga qo'shishi kerak")


@router.get("/tests")
def api_get_tests(subject: str = None, user=Depends(get_verified_telegram_user)):
    tests = db.get_all_tests(subject=subject, include_control=False)
    for t in tests:
        t["question_count"] = db.count_test_questions(t["id"])
    return {"tests": tests}


@router.get("/test/{test_id}")
def api_get_test(test_id: int, user=Depends(get_verified_telegram_user)):
    test = db.get_test(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test topilmadi")
    if test.get("is_control_test"):
        _ensure_control_test_access(test, user["telegram_id"])
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


@router.post("/test/{test_id}/start")
def api_start_test(test_id: int, user=Depends(get_verified_telegram_user)):
    test = db.get_test(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test topilmadi")
    if test.get("is_control_test"):
        _ensure_control_test_access(test, user["telegram_id"])
    telegram_id = user["telegram_id"]
    db.get_or_create_user(telegram_id, user["first_name"], user.get("username"))
    attempt_id = db.start_attempt(telegram_id, test_id)
    return {"attempt_id": attempt_id}


def _get_owned_attempt_or_403(attempt_id: int, telegram_id: int) -> dict:
    """Bu urinish (attempt) haqiqatan ham so'rov yuborayotgan foydalanuvchiga
    tegishli ekanligini tekshiradi — aks holda birov boshqa birovning testiga
    'javob qo'shib qo'yishi' mumkin edi."""
    attempt = db.get_attempt(attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Urinish topilmadi")
    if attempt["telegram_id"] != telegram_id:
        raise HTTPException(status_code=403, detail="Bu urinish sizga tegishli emas")
    return attempt


@router.post("/attempt/{attempt_id}/answer")
def api_submit_answer(attempt_id: int, data: dict = Body(...), user=Depends(get_verified_telegram_user)):
    telegram_id = user["telegram_id"]
    _get_owned_attempt_or_403(attempt_id, telegram_id)
    question_id = int(data["question_id"])
    selected_index = int(data["selected_index"])
    db.get_or_create_user(telegram_id, user["first_name"], user.get("username"))
    result = db.submit_answer(telegram_id, attempt_id, question_id, selected_index)
    return result


@router.post("/attempt/{attempt_id}/finish")
def api_finish_attempt(attempt_id: int, user=Depends(get_verified_telegram_user)):
    _get_owned_attempt_or_403(attempt_id, user["telegram_id"])
    result = db.finish_attempt(attempt_id)
    if not result:
        raise HTTPException(status_code=404, detail="Urinish topilmadi")
    return result


@router.get("/attempt/{attempt_id}/grid")
def api_get_attempt_grid(attempt_id: int, user=Depends(get_verified_telegram_user)):
    """Nazorat testi yakunlangach, har bir savol bo'yicha to'g'ri/noto'g'ri
    katakchalar jadvalini qaytaradi (natija ekranidagi 'Savollar natijasi')."""
    _get_owned_attempt_or_403(attempt_id, user["telegram_id"])
    return {"grid": db.get_attempt_answers_grid(attempt_id)}


@router.get("/my-test-results")
def api_my_test_results(user=Depends(get_verified_telegram_user)):
    return {"results": db.get_user_test_results(user["telegram_id"])}
