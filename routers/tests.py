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


def _ensure_practice_group_unlocked(test: dict, telegram_id: int):
    """Mavzuli test BOSQICHLARI ('1-bo'lim', '2-bo'lim'...) KETMA-KET
    ochiladi (avvalgi bosqichdagi barcha turkumlar/testlar tugatilmaguncha
    keyingisi qulflangan). Bosqich ICHIDAGI turkumlar (masalan
    "Mavzulashtirilgan testlar"/"Nazorat testlari") esa bir-biriga nisbatan
    qulflanmaydi. Frontend qulflangan bosqichga kirish tugmasini
    ko'rsatmaydi, lekin haqiqiy himoya shu yerda — to'g'ridan-to'g'ri so'rov
    yuborilsa ham chetlab o'tib bo'lmaydi."""
    group_id = test.get("test_group_id")
    if not group_id:
        return  # eski/guruhsiz testlar cheklovsiz qoladi
    group = db.get_test_group(group_id)
    if not group:
        return
    stage_id = group.get("stage_id")
    if not stage_id:
        return  # bosqichga hali bog'lanmagan guruh — cheklovsiz qoladi
    stage = db.get_test_stage(stage_id)
    if not stage:
        return
    stages = db.compute_stages_with_unlock(telegram_id, stage["subject_card_id"])
    this_stage = next((s for s in stages if s["id"] == stage_id), None)
    if this_stage and not this_stage["unlocked"]:
        raise HTTPException(status_code=403, detail="Bu bo'lim sizga hali ochilmagan — avvalgi bo'limdagi testlarni tugating")


@router.get("/test-subject-cards")
def api_get_test_subject_cards():
    return {"cards": db.get_test_subject_cards(only_active=True)}


@router.get("/test-subject-cards/{card_id}/stages")
def api_get_test_stages(card_id: int, user=Depends(get_verified_telegram_user)):
    """Fan ichidagi bosqichlar ('1-bo'lim', '2-bo'lim'...) — ketma-ket
    ochiladi."""
    stages = db.compute_stages_with_unlock(user["telegram_id"], card_id)
    return {"stages": stages}


@router.get("/test-stages/{stage_id}/groups")
def api_get_stage_groups(stage_id: int, user=Depends(get_verified_telegram_user)):
    """Bosqich ICHIDAGI turkumlar (masalan "Mavzulashtirilgan testlar",
    "Nazorat testlari") — bir-biriga nisbatan qulflanmaydi."""
    groups = db.get_groups_with_progress(user["telegram_id"], stage_id)
    return {"groups": groups}


@router.get("/tests")
def api_get_tests(subject: str = None, group_id: int = None, user=Depends(get_verified_telegram_user)):
    # Faqat "oddiy/mavzuli" testlar — Attestatsiya alohida /api/attestation-tests
    # orqali, Nazorat testlari esa /api/control-tests orqali ko'rsatiladi.
    tests = db.get_all_tests(subject=subject, include_control=False, test_kind="practice")
    if group_id is not None:
        tests = [t for t in tests if t.get("test_group_id") == group_id]
    for t in tests:
        t["question_count"] = db.count_test_questions(t["id"])
    return {"tests": tests}


@router.get("/attestation-tests")
def api_get_attestation_tests(subject: str = None, user=Depends(get_verified_telegram_user)):
    # @biologiyamockbot'dagi kabi — Attestatsiya testlari "Erkin kirish"
    # (hech qanday tayinlash/kursga yozilish shart emas, har bir talaba
    # ochib ishlashi mumkin).
    tests = db.get_all_tests(subject=subject, test_kind="attestation")
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
    else:
        _ensure_practice_group_unlocked(test, user["telegram_id"])
    questions = db.get_questions(test_id)
    safe_questions = []
    for q in questions:
        safe_questions.append({
            "id": q["id"], "question_text": q["question_text"], "image_url": q["image_url"],
            "table_data": q.get("table_data"),
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
    else:
        _ensure_practice_group_unlocked(test, user["telegram_id"])
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
    # Nazorat testida talaba mashq uchun qayta ishlashi mumkin, lekin
    # oylik reytingga faqat BIRINCHI yakunlangan urinish kiradi — frontend
    # shu belgi orqali "bu urinish reytingga hisoblandimi" ko'rsatadi.
    result["counts_for_ranking"] = db.is_first_finished_attempt(attempt_id)
    return result


@router.get("/attempt/{attempt_id}/grid")
def api_get_attempt_grid(attempt_id: int, user=Depends(get_verified_telegram_user)):
    """Nazorat testi yakunlangach, har bir savol bo'yicha to'g'ri/noto'g'ri
    katakchalar jadvalini qaytaradi (natija ekranidagi 'Savollar natijasi')."""
    _get_owned_attempt_or_403(attempt_id, user["telegram_id"])
    return {"grid": db.get_attempt_answers_grid(attempt_id)}


@router.post("/attempt/{attempt_id}/flag")
def api_flag_question(attempt_id: int, data: dict = Body(...), user=Depends(get_verified_telegram_user)):
    """Attestatsiya: savolni "keyinroq qaytish uchun" belgilash/bekor qilish
    (@biologiyamockbot'dagi "Belgilash" tugmasi kabi)."""
    _get_owned_attempt_or_403(attempt_id, user["telegram_id"])
    question_id = int(data["question_id"])
    flagged = bool(data.get("flagged"))
    return db.set_answer_flag(attempt_id, question_id, flagged)


@router.post("/attempt/{attempt_id}/objection")
def api_submit_objection(attempt_id: int, data: dict = Body(...), user=Depends(get_verified_telegram_user)):
    """Attestatsiya: savolga e'tiroz/shikoyat yozish — admin panelda ko'riladi."""
    _get_owned_attempt_or_403(attempt_id, user["telegram_id"])
    question_id = int(data["question_id"])
    comment = (data.get("comment") or "").strip()
    if not comment:
        raise HTTPException(status_code=400, detail="E'tiroz matnini yozing")
    obj_id = db.create_objection(attempt_id, question_id, user["telegram_id"], comment)
    return {"id": obj_id}


@router.get("/attempt/{attempt_id}/rank")
def api_get_attempt_rank(attempt_id: int, user=Depends(get_verified_telegram_user)):
    """Attestatsiya: shu variant bo'yicha "X-o'rin / Y talaba ichida" reyting."""
    _get_owned_attempt_or_403(attempt_id, user["telegram_id"])
    return {"rank": db.get_attempt_rank(attempt_id)}


@router.get("/my-test-results")
def api_my_test_results(user=Depends(get_verified_telegram_user)):
    return {"results": db.get_user_test_results(user["telegram_id"])}
