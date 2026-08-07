# routers/bio_game.py
# ==========================================================================
#  BIOLOGIYA O'YINI — talaba uchun endpointlar
# ==========================================================================
# KIMYODAN ASOSIY FARQ: bosqichlar ro'yxati QAT'IY EMAS. Har level
# o'zida qanday ma'lumot bo'lsa, shunga mos o'yinlarni beradi
# (database.py -> bio_available_stages).
#
# BAHOLASH: barcha bosqichlar mashq, shuning uchun test/juftlash kabi
# oddiy turlarda to'g'ri javob mijozga yuboriladi (darhol qizil/yashil
# ko'rsatish uchun). LEKIN yakuniy ball baribir SERVERDA qayta
# hisoblanadi. Ketma-ketlik, guruhlash, "Kim men?" va rasm o'yinlarida
# esa javob umuman yuborilmaydi — ular bir necha urinishli o'yin bo'lgani
# uchun javobni ko'rish o'yinni butunlay buzardi.

from fastapi import APIRouter, Depends, HTTPException, Body, Query

from routers.deps import get_verified_telegram_user
import database as db
import bio_questions as bq

router = APIRouter(prefix="/api/bio", tags=["bio-game"])


# --------------------------------------------------------------------------
#  HUB va mavzular
# --------------------------------------------------------------------------

@router.get("/hub")
def api_bio_hub(user=Depends(get_verified_telegram_user)):
    tid = user["telegram_id"]
    topics = db.get_bio_topics()

    out, earned_all, total_all = [], 0, 0
    for t in topics:
        item = {
            "id": t["id"], "key": t["key"], "title": t["title"],
            "subtitle": t["subtitle"], "icon": t["icon"],
            "is_ready": bool(t["is_ready"]),
            "earned_stars": 0, "total_stars": 0,
            "level_count": 0, "term_count": 0,
        }
        if t["is_ready"]:
            path = db.build_bio_level_path(tid, t["id"])
            item.update({
                "earned_stars": path["earned_stars"],
                "total_stars": path["total_stars"],
                "level_count": path["level_count"],
                "term_count": path["term_count"],
            })
            earned_all += path["earned_stars"]
            total_all += path["total_stars"]
        out.append(item)

    return {"topics": out, "earned_stars": earned_all, "total_stars": total_all}


@router.get("/topic/{topic_id}/path")
def api_bio_path(topic_id: int, user=Depends(get_verified_telegram_user)):
    topic = db.get_bio_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Mavzu topilmadi")
    if not topic["is_ready"]:
        raise HTTPException(status_code=403, detail="Bu bo'lim hali tayyorlanmoqda")
    return {"topic": topic, **db.build_bio_level_path(user["telegram_id"], topic_id)}


# --------------------------------------------------------------------------
#  Level va bosqichlar
# --------------------------------------------------------------------------

def _require_unlocked(telegram_id: int, level: dict, level_id: int):
    """Qulf SERVERDA tekshiriladi — mijozdagi ikonkani chetlab o'tib bo'lmaydi."""
    path = db.build_bio_level_path(telegram_id, level["topic_id"])
    for lv in path["levels"]:
        if lv["id"] == level_id:
            if not lv["unlocked"]:
                raise HTTPException(status_code=403,
                                    detail="Bu level hali ochilmagan — avvalgisini yakunlang")
            return
    raise HTTPException(status_code=404, detail="Level topilmadi")


@router.get("/level/{level_id}")
def api_bio_level(level_id: int, user=Depends(get_verified_telegram_user)):
    tid = user["telegram_id"]
    detail = db.get_bio_level_detail(tid, level_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Level topilmadi")
    _require_unlocked(tid, detail["level"], level_id)

    terms = db.get_bio_terms(level_id)
    return {
        "level": detail["level"],
        "stages": detail["stages"],
        "next_stage": detail["next_stage"],
        "all_done": detail["all_done"],
        "term_count": detail["stats"]["term_count"],
        "preview_terms": [t["term"] for t in terms[:4]],
    }


@router.get("/level/{level_id}/stage/{stage_key}")
def api_bio_stage(level_id: int, stage_key: str,
                  user=Depends(get_verified_telegram_user)):
    """Bosqich ma'lumotini generatsiya qilib beradi.

    Har chaqirilganda qayta yasaladi va aralashtiriladi — o'quvchi
    tartibni emas, mazmunni o'rganadi.
    """
    tid = user["telegram_id"]
    detail = db.get_bio_level_detail(tid, level_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Level topilmadi")
    _require_unlocked(tid, detail["level"], level_id)

    stage = next((s for s in detail["stages"] if s["key"] == stage_key), None)
    if not stage:
        raise HTTPException(status_code=400,
                            detail="Bu levelda bunday o'yin yo'q")
    if not stage["unlocked"]:
        raise HTTPException(status_code=403, detail="Bu bosqich hali ochilmagan")

    terms = db.get_bio_terms(level_id)
    pool = db.get_bio_terms_by_topic(detail["level"]["topic_id"]) or terms

    payload = {
        "level": detail["level"],
        "stage": stage_key,
        "stage_title": db.BIO_STAGE_TITLES[stage_key],
    }

    if stage_key == "learn":
        payload["cards"] = bq.build_learn_cards(terms)
        payload["total"] = len(payload["cards"])

    elif stage_key == "test":
        qs = bq.build_test_questions(terms, pool=pool)
        payload["questions"] = qs           # mashq — javob ko'rsatiladi
        payload["total"] = len(qs)

    elif stage_key == "match":
        boards = bq.build_match_boards(terms, per_board=5)
        payload["boards"] = boards
        payload["total"] = sum(len(b["left"]) for b in boards)

    elif stage_key == "sequence":
        tasks = bq.build_sequence_tasks(db.get_bio_sequences(level_id))
        payload["tasks"] = tasks            # to'g'ri tartib YUBORILMAYDI
        payload["total"] = len(tasks)

    elif stage_key == "group":
        task = bq.build_group_task(terms)
        if not task:
            raise HTTPException(status_code=400, detail="Guruhlash uchun ma'lumot yetarli emas")
        payload["task"] = {k: v for k, v in task.items() if k != "answer_key"}
        payload["total"] = task["total"]

    elif stage_key == "whoami":
        tasks = bq.build_whoami_tasks(terms, pool=pool)
        payload["tasks"] = tasks            # javob YUBORILMAYDI
        payload["total"] = len(tasks)
        payload["max_points"] = bq.WHOAMI_MAX_POINTS

    elif stage_key == "image":
        tasks = bq.build_image_tasks(db.get_bio_image_tasks(level_id))
        payload["tasks"] = tasks            # qaysi nuqta qaysi nom — yashirin
        payload["total"] = sum(t["total"] for t in tasks)

    return payload


# --------------------------------------------------------------------------
#  Javoblarni tekshirish (yangi o'yin turlari uchun)
# --------------------------------------------------------------------------

@router.post("/level/{level_id}/check/sequence")
def api_check_sequence(level_id: int, data: dict = Body(...),
                       user=Depends(get_verified_telegram_user)):
    """Ketma-ketlikni tekshiradi va NECHTASI JOYIDA ekanini aytadi."""
    seq_id = db.safe_int(data.get("sequence_id"))
    sequences = {s["id"]: s for s in db.get_bio_sequences(level_id)}
    if seq_id not in sequences:
        raise HTTPException(status_code=404, detail="Ketma-ketlik topilmadi")
    return bq.check_sequence(data.get("order"), sequences[seq_id]["steps"])


@router.post("/level/{level_id}/check/group")
def api_check_group(level_id: int, data: dict = Body(...),
                    user=Depends(get_verified_telegram_user)):
    """Bitta elementning guruhini tekshiradi (o'yin davomida, bittalab)."""
    term = db.get_bio_term(db.safe_int(data.get("term_id")))
    if not term or term["level_id"] != level_id:
        raise HTTPException(status_code=404, detail="Element topilmadi")
    expected = (term.get("group_name") or "").strip().lower()
    given = (data.get("group") or "").strip().lower()
    return {"correct": bool(expected) and expected == given,
            "correct_group": term.get("group_name")}


@router.post("/level/{level_id}/check/whoami")
def api_check_whoami(level_id: int, data: dict = Body(...),
                     user=Depends(get_verified_telegram_user)):
    """"Kim men?" javobini tekshiradi va nechanchi ipuchada topganiga
    qarab ball beradi."""
    term = db.get_bio_term(db.safe_int(data.get("term_id")))
    if not term or term["level_id"] != level_id:
        raise HTTPException(status_code=404, detail="Termin topilmadi")
    given = (data.get("answer") or "").strip().lower()
    is_correct = given == (term["term"] or "").strip().lower()
    clue_index = max(0, db.safe_int(data.get("clue_index")))
    return {
        "correct": is_correct,
        "correct_answer": term["term"],
        "points": bq.whoami_points(clue_index) if is_correct else 0,
        "max_points": bq.WHOAMI_MAX_POINTS,
    }


@router.post("/level/{level_id}/check/image")
def api_check_image(level_id: int, data: dict = Body(...),
                    user=Depends(get_verified_telegram_user)):
    """Rasmdagi nuqta va nom mosligini tekshiradi."""
    task_id = db.safe_int(data.get("task_id"))
    tasks = {t["id"]: t for t in db.get_bio_image_tasks(level_id)}
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Topshiriq topilmadi")
    labels = tasks[task_id]["labels"]
    idx = db.safe_int(data.get("point_index"))
    ok = bq.check_image_answer(labels, idx, data.get("name"))
    correct_name = labels[idx]["name"] if 0 <= idx < len(labels) else None
    return {"correct": ok, "correct_name": correct_name}


# --------------------------------------------------------------------------
#  Bosqich yakuni
# --------------------------------------------------------------------------

@router.post("/level/{level_id}/stage/{stage_key}/submit")
def api_bio_submit(level_id: int, stage_key: str, data: dict = Body(...),
                   user=Depends(get_verified_telegram_user)):
    """Bosqich natijasini saqlaydi.

    MIJOZDAGI BALLGA ISHONILMAYDI:
      - test/match  — server har javobni bazadan qayta tekshiradi
      - sequence/group/whoami/image — bu o'yinlarda har javob ALLAQACHON
        server orqali tekshirilgan (yuqoridagi /check/* endpointlari),
        shuning uchun bu yerda faqat sanoq qabul qilinadi, lekin u
        umumiy sondan oshib keta olmaydi.
    """
    tid = user["telegram_id"]
    detail = db.get_bio_level_detail(tid, level_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Level topilmadi")
    _require_unlocked(tid, detail["level"], level_id)
    if not any(s["key"] == stage_key for s in detail["stages"]):
        raise HTTPException(status_code=400, detail="Bu levelda bunday o'yin yo'q")

    terms = {t["id"]: t for t in db.get_bio_terms(level_id)}

    if stage_key == "learn":
        correct = total = len(terms)
    elif stage_key in ("test", "match"):
        answers = data.get("answers") or []
        total = len(answers)
        correct = sum(1 for a in answers if _is_correct(a, terms))
    else:
        # Server allaqachon tekshirgan o'yinlar — sanoqni chegaralaymiz.
        total = max(0, db.safe_int(data.get("total")))
        correct = max(0, min(total, db.safe_int(data.get("correct"))))

    result = db.save_bio_stage_result(tid, level_id, stage_key, correct, total)

    coins = 0
    if result["attempts"] == 1:
        coins = _stage_reward(stage_key, correct, total)
        if coins:
            db.add_coins(tid, coins)
    try:
        db.record_daily_activity(tid)
    except Exception:
        pass

    after = db.get_bio_level_detail(tid, level_id)
    return {
        "correct": correct, "total": total,
        "accuracy": round(correct / total * 100) if total else 0,
        "stars": result["stars"], "best_stars": result["best_stars"],
        "improved": result["improved"], "coins_earned": coins,
        "next_stage": after["next_stage"],
        "level_completed": after["all_done"],
    }


def _is_correct(answer: dict, terms: dict) -> bool:
    t = terms.get(db.safe_int(answer.get("term_id")))
    if not t:
        return False
    given = (answer.get("answer") or "").strip().lower()
    if not given:
        return False
    q_type = answer.get("type")
    if q_type in (bq.Q_TERM_BY_DEF, bq.Q_TERM_BY_FUNC, "match"):
        return given == (t["term"] or "").strip().lower()
    if q_type == bq.Q_DEF_BY_TERM:
        return given == (t.get("definition") or "").strip().lower()
    if q_type == bq.Q_FUNC_BY_TERM:
        return given == (t.get("function_text") or "").strip().lower()
    if q_type == bq.Q_GROUP_BY_TERM:
        return given == (t.get("group_name") or "").strip().lower()
    return False


def _stage_reward(stage_key: str, correct: int, total: int) -> int:
    """Coin. Yangi o'yin turlari biroz ko'proq beradi — ular qiyinroq
    va o'quvchini ularni sinab ko'rishga undash kerak."""
    if stage_key == "learn":
        return 5
    if not total:
        return 0
    ratio = correct / total
    base = 25 if ratio >= 0.9 else 18 if ratio >= 0.7 else 12 if ratio >= 0.5 else 6
    if stage_key in ("sequence", "group", "whoami", "image"):
        base += 5
    return base


# --------------------------------------------------------------------------
#  Biologiya lug'ati
# --------------------------------------------------------------------------

@router.get("/dictionary")
def api_bio_dictionary(q: str = Query(default=""), limit: int = Query(default=60),
                       offset: int = Query(default=0),
                       user=Depends(get_verified_telegram_user)):
    limit = max(1, min(db.safe_int(limit, 60), 200))
    items = db.search_bio_terms(q, limit=limit, offset=max(0, db.safe_int(offset)))
    return {
        "items": [{
            "id": t["id"], "term": t["term"], "definition": t["definition"],
            "group_name": t["group_name"], "level_title": t["level_title"],
        } for t in items],
        "query": q,
    }


@router.get("/term/{term_id}")
def api_bio_term(term_id: int, user=Depends(get_verified_telegram_user)):
    t = db.get_bio_term(term_id)
    if not t:
        raise HTTPException(status_code=404, detail="Termin topilmadi")
    # Ipuchalarni lug'atda ko'rsatmaymiz — "Kim men?" o'yinini buzmasligi uchun.
    t.pop("clues", None)
    return t
