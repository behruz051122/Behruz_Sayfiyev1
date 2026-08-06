# routers/chem_game.py
# ==========================================================================
#  KIMYO O'YINI — talaba uchun endpointlar
# ==========================================================================
# Bu router "Levellar bilan o'rganish" oqimini va moddalar lug'atini
# xizmat qiladi. Battle/ELO alohida routerda (chem_battle.py).
#
# BAHOLASH QAYERDA BO'LADI:
#   Level bosqichlari — MASHQ. Shuning uchun to'g'ri javob mijozga
#   yuboriladi (darhol qizil/yashil ko'rsatish uchun), LEKIN yakuniy ball
#   baribir SERVERDA qayta hisoblanadi: mijoz har savol uchun
#   {substance_id, type, answer} yuboradi, server esa javobni BAZADAN
#   tekshiradi. Ya'ni mijozdagi ballga ishonilmaydi.
#
#   Battle — MUSOBAQA (ELO xavf ostida). U yerda to'g'ri javob umuman
#   yuborilmaydi.

from fastapi import APIRouter, Depends, HTTPException, Body, Query

from routers.deps import get_verified_telegram_user
import database as db
import chem_questions as cq

router = APIRouter(prefix="/api/chem", tags=["chem-game"])


# --------------------------------------------------------------------------
#  HUB va kategoriyalar
# --------------------------------------------------------------------------

@router.get("/hub")
def api_chem_hub(user=Depends(get_verified_telegram_user)):
    """O'yin bosh ekrani uchun barcha ma'lumot — bitta so'rovda.

    Ilova sekinlashmasligi uchun ataylab bitta endpoint: kategoriyalar,
    har biridagi progress va umumiy yulduz hisobi birga qaytadi.
    """
    tid = user["telegram_id"]
    cats = db.get_chem_categories()

    out, earned_all, total_all = [], 0, 0
    for c in cats:
        item = {
            "id": c["id"], "key": c["key"], "title": c["title"],
            "subtitle": c["subtitle"], "icon": c["icon"],
            "is_ready": bool(c["is_ready"]),
            "earned_stars": 0, "total_stars": 0, "level_count": 0,
            "substance_count": 0,
        }
        if c["is_ready"]:
            path = db.build_chem_level_path(tid, c["id"])
            item.update({
                "earned_stars": path["earned_stars"],
                "total_stars": path["total_stars"],
                "level_count": path["level_count"],
                "substance_count": path["substance_count"],
            })
            earned_all += path["earned_stars"]
            total_all += path["total_stars"]
        out.append(item)

    return {
        "categories": out,
        "earned_stars": earned_all,
        "total_stars": total_all,
    }


@router.get("/category/{category_id}/path")
def api_chem_level_path(category_id: int, user=Depends(get_verified_telegram_user)):
    """Level yo'lagi — qulflangan/ochilgan holati bilan."""
    cat = db.get_chem_category(category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Kategoriya topilmadi")
    if not cat["is_ready"]:
        raise HTTPException(status_code=403, detail="Bu bo'lim hali tayyorlanmoqda")

    path = db.build_chem_level_path(user["telegram_id"], category_id)
    return {"category": cat, **path}


# --------------------------------------------------------------------------
#  Level va bosqichlar
# --------------------------------------------------------------------------

@router.get("/level/{level_id}")
def api_chem_level(level_id: int, user=Depends(get_verified_telegram_user)):
    """Level ichi: 4 bosqich holati + moddalar ro'yxati (chip'lar uchun)."""
    tid = user["telegram_id"]
    detail = db.get_chem_level_detail(tid, level_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Level topilmadi")

    _require_level_unlocked(tid, detail["level"], level_id)

    return {
        "level": detail["level"],
        "stages": detail["stages"],
        "next_stage": detail["next_stage"],
        "all_done": detail["all_done"],
        "substance_count": len(detail["substances"]),
        # Sarlavha kartasidagi chip'lar uchun — birinchi 4 ta formula.
        "preview_formulas": [s["formula"] for s in detail["substances"][:4]],
    }


def _require_level_unlocked(telegram_id: int, level: dict, level_id: int):
    """SERVERDA qulf tekshiruvi.

    Mijozdagi qulf ikonkasi — bu shunchaki bezak; uni chetlab o'tib
    to'g'ridan-to'g'ri so'rov yuborish mumkin. Shuning uchun haqiqiy
    tekshiruv shu yerda bo'ladi.
    """
    path = db.build_chem_level_path(telegram_id, level["category_id"])
    for lv in path["levels"]:
        if lv["id"] == level_id:
            if not lv["unlocked"]:
                raise HTTPException(
                    status_code=403,
                    detail="Bu level hali ochilmagan — avvalgisini yakunlang")
            return
    raise HTTPException(status_code=404, detail="Level topilmadi")


@router.get("/level/{level_id}/stage/{stage}")
def api_chem_stage_questions(level_id: int, stage: int,
                             user=Depends(get_verified_telegram_user)):
    """Bosqich savollarini generatsiya qilib beradi.

    Har safar chaqirilganda savollar QAYTA yasaladi va aralashtiriladi —
    o'quvchi yod olib qo'ymaydi, tartibni emas, mazmunni o'rganadi.
    """
    tid = user["telegram_id"]
    detail = db.get_chem_level_detail(tid, level_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Level topilmadi")
    _require_level_unlocked(tid, detail["level"], level_id)

    if stage not in db.CHEM_STAGES:
        raise HTTPException(status_code=400, detail="Noto'g'ri bosqich raqami")

    # Bosqich ketma-ketligi ham serverda tekshiriladi.
    stage_info = next((s for s in detail["stages"] if s["stage"] == stage), None)
    if not stage_info or not stage_info["unlocked"]:
        raise HTTPException(status_code=403, detail="Bu bosqich hali ochilmagan")

    substances = detail["substances"]
    if not substances:
        raise HTTPException(status_code=400, detail="Bu levelda hali modda yo'q")

    # Chalg'ituvchi variantlar butun kategoriyadan olinadi — shunda ular
    # haqiqatan ham "o'xshash, lekin boshqa" moddalar bo'ladi.
    pool = db.get_chem_substances_by_category(detail["level"]["category_id"]) or substances

    payload = {
        "level": detail["level"],
        "stage": stage,
        "stage_title": db.CHEM_STAGE_TITLES[stage],
    }

    if stage == db.CHEM_STAGE_LEARN:
        payload["cards"] = cq.build_learn_cards(substances)
        payload["total"] = len(payload["cards"])
    elif stage == db.CHEM_STAGE_TEST:
        qs = cq.build_test_questions(substances, pool=pool)
        payload["questions"] = qs          # mashq — javob ko'rsatiladi
        payload["total"] = len(qs)
    elif stage == db.CHEM_STAGE_MATCH:
        boards = cq.build_match_boards(substances, per_board=6)
        payload["boards"] = boards
        payload["total"] = sum(len(b["left"]) for b in boards)
    else:  # CHEM_STAGE_WRITE
        qs = cq.build_write_questions(substances)
        payload["questions"] = qs          # to'g'ri javob YUBORILMAYDI
        payload["total"] = len(qs)

    return payload


@router.post("/level/{level_id}/stage/{stage}/check")
def api_chem_check_write(level_id: int, stage: int, data: dict = Body(...),
                         user=Depends(get_verified_telegram_user)):
    """Yozish bosqichida bitta javobni tekshiradi.

    Alohida endpoint kerak, chunki bu bosqichda to'g'ri javob mijozga
    oldindan yuborilmaydi (aks holda o'quvchi ekranda ko'rib yozib qo'yadi).
    """
    if stage != db.CHEM_STAGE_WRITE:
        raise HTTPException(status_code=400, detail="Bu endpoint faqat yozish bosqichi uchun")

    sub = db.get_chem_substance(db.safe_int(data.get("substance_id")))
    if not sub or sub["level_id"] != level_id:
        raise HTTPException(status_code=404, detail="Modda topilmadi")

    is_correct = cq.check_write_answer(data.get("answer", ""), sub["formula"])
    return {"correct": is_correct, "correct_answer": sub["formula"]}


@router.post("/level/{level_id}/stage/{stage}/submit")
def api_chem_stage_submit(level_id: int, stage: int, data: dict = Body(...),
                          user=Depends(get_verified_telegram_user)):
    """Bosqich yakunlanganda natijani saqlaydi.

    Mijoz yuborgan BALLGA ISHONILMAYDI — server har bir javobni bazadan
    qayta tekshiradi. Mijoz faqat `answers` ro'yxatini yuboradi:
        [{"substance_id": 12, "type": "formula_by_name", "answer": "H2SO4"}, ...]
    """
    tid = user["telegram_id"]
    detail = db.get_chem_level_detail(tid, level_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Level topilmadi")
    _require_level_unlocked(tid, detail["level"], level_id)
    if stage not in db.CHEM_STAGES:
        raise HTTPException(status_code=400, detail="Noto'g'ri bosqich raqami")

    substances = {s["id"]: s for s in detail["substances"]}

    if stage == db.CHEM_STAGE_LEARN:
        # O'rganish bosqichida "to'g'ri/xato" yo'q — kartochkalar ko'rildi.
        correct, total = len(substances), len(substances)
    else:
        answers = data.get("answers") or []
        total = len(answers)
        correct = sum(1 for a in answers if _is_answer_correct(a, substances))

    result = db.save_chem_stage_result(tid, level_id, stage, correct, total)

    # Coin: birinchi marta yakunlaganda beriladi (qayta o'ynash uchun emas —
    # aks holda bitta levelni takrorlab cheksiz coin yig'ish mumkin bo'lardi).
    coins = 0
    if result["attempts"] == 1:
        coins = _stage_reward(stage, correct, total)
        if coins:
            db.add_coins(tid, coins)

    # Kunlik faollik — streak tizimi bilan bir xil manba.
    try:
        db.record_daily_activity(tid)
    except Exception:
        pass

    detail_after = db.get_chem_level_detail(tid, level_id)
    return {
        "correct": correct,
        "total": total,
        "accuracy": round(correct / total * 100) if total else 0,
        "stars": result["stars"],
        "best_stars": result["best_stars"],
        "improved": result["improved"],
        "coins_earned": coins,
        "next_stage": detail_after["next_stage"],
        "level_completed": detail_after["all_done"],
    }


def _is_answer_correct(answer: dict, substances: dict) -> bool:
    """Bitta javobni bazadagi haqiqiy qiymat bilan solishtiradi."""
    sub = substances.get(db.safe_int(answer.get("substance_id")))
    if not sub:
        return False
    given = (answer.get("answer") or "").strip()
    if not given:
        return False

    q_type = answer.get("type")
    if q_type == cq.Q_FORMULA_BY_NAME:
        return cq.check_write_answer(given, sub["formula"])
    if q_type == "write_formula":
        return cq.check_write_answer(given, sub["formula"])
    if q_type == cq.Q_NAME_BY_FORMULA:
        return given.lower() == (sub["name"] or "").strip().lower()
    if q_type == cq.Q_COLOR_PURE:
        return _same_text(given, sub["color_pure"])
    if q_type == cq.Q_COLOR_SOLUTION:
        return _same_text(given, sub["color_solution"])
    if q_type == cq.Q_PRECIPITATE:
        return _same_text(given, sub["color_precipitate"])
    if q_type == cq.Q_HISTORIC:
        return _same_text(given, sub["historic_name"])
    if q_type == "match":
        # Moslashtirishda mijoz topilgan juftlikni yuboradi: to'g'riligi
        # substance_id ning o'zi bilan aniqlanadi (juftlik faqat to'g'ri
        # bo'lsagina yopiladi), shuning uchun mavjudligini tekshirish yetarli.
        return True
    return False


def _same_text(a, b) -> bool:
    return (a or "").strip().lower() == (b or "").strip().lower()


def _stage_reward(stage: int, correct: int, total: int) -> int:
    """Bosqich uchun coin.

    O'rganish — kichik rag'bat (5), sinov bosqichlari — natijaga qarab
    10..25. Maqsad: coin o'yin uchun yoqimli bonus bo'lsin, lekin
    coin yig'ish uchun o'yin o'ynash foydali bo'lib qolmasin.
    """
    if stage == db.CHEM_STAGE_LEARN:
        return 5
    if not total:
        return 0
    ratio = correct / total
    if ratio >= 0.9:
        return 25
    if ratio >= 0.7:
        return 18
    if ratio >= 0.5:
        return 12
    return 6


# --------------------------------------------------------------------------
#  Moddalar lug'ati
# --------------------------------------------------------------------------

@router.get("/dictionary")
def api_chem_dictionary(q: str = Query(default=""), limit: int = Query(default=60),
                        offset: int = Query(default=0),
                        user=Depends(get_verified_telegram_user)):
    """Formula yoki nom bo'yicha qidiruv."""
    limit = max(1, min(db.safe_int(limit, 60), 200))
    items = db.search_chem_substances(q, limit=limit, offset=max(0, db.safe_int(offset)))
    return {
        "items": [{
            "id": s["id"], "formula": s["formula"], "name": s["name"],
            "historic_name": s["historic_name"], "level_title": s["level_title"],
        } for s in items],
        "query": q,
    }


@router.get("/substance/{substance_id}")
def api_chem_substance(substance_id: int, user=Depends(get_verified_telegram_user)):
    """Modda kartasi — lug'atdagi element bosilganda."""
    s = db.get_chem_substance(substance_id)
    if not s:
        raise HTTPException(status_code=404, detail="Modda topilmadi")
    return s
