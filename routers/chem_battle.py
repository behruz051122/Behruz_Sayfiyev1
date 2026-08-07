# routers/chem_battle.py
# ==========================================================================
#  KIMYO O'YINI — BATTLE (1v1), bot bilan mashq, do'stga taklif, reyting
# ==========================================================================
# MODEL — ASINXRON. Ikkala o'yinchi bir vaqtda onlayn bo'lishi shart emas:
#   1) "Battle" bosilganda, agar shu kategoriyada raqib KUTAYOTGAN jang
#      bo'lsa — unga qo'shilamiz va AYNAN SHU savollarga javob beramiz.
#   2) Bo'lmasa — yangi jang yaratiladi, siz javob berasiz va "raqib
#      kutilmoqda" holatida qolasiz. Keyinroq kimdir qo'shilganda natija
#      chiqadi va Telegram orqali xabar keladi.
#   3) 10 daqiqada hech kim qo'shilmasa — fon vazifasi "Kimyobot" ni
#      raqib qilib qo'yadi, jang osilib qolmaydi.
#
# XAVFSIZLIK: battle — MUSOBAQA (ELO xavf ostida), shuning uchun to'g'ri
# javob mijozga HECH QACHON yuborilmaydi. Har savol alohida so'raladi va
# javob serverda tekshiriladi. Vaqtni ham server o'lchaydi.

import random
import string
import time

from fastapi import APIRouter, Depends, HTTPException, Body

from routers.deps import get_verified_telegram_user
import database as db
import chem_questions as cq

router = APIRouter(prefix="/api/chem/battle", tags=["chem-battle"])

# Savol berilgan vaqtni server xotirasida saqlaymiz — mijoz yuborgan
# "men 2 soniyada javob berdim" degan da'voga ishonib bo'lmaydi.
# {(battle_id, telegram_id): {"index": n, "asked_at": ts, "score": n, "time_ms": n}}
_RUNS = {}


def _run_key(battle_id, telegram_id):
    return f"{battle_id}:{telegram_id}"


def _new_code():
    """Do'stga yuborish uchun 6 belgili kod (chalkashadigan harflarsiz)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # I, O, 0, 1 yo'q
    return "".join(random.choice(alphabet) for _ in range(6))


def _pool_for(category_id: int):
    pool = db.get_chem_substances_by_category(category_id)
    if len(pool) < 4:
        raise HTTPException(
            status_code=400,
            detail="Battle uchun kamida 4 ta modda kerak — o'qituvchi bazani to'ldirmoqda.")
    return pool


def _ready_category():
    """Battle o'ynaladigan birinchi tayyor kategoriya."""
    cats = [c for c in db.get_chem_categories(only_ready=True)]
    if not cats:
        raise HTTPException(status_code=400, detail="Hozircha o'yinga tayyor bo'lim yo'q.")
    return cats[0]


# --------------------------------------------------------------------------
#  Jang boshlash
# --------------------------------------------------------------------------

@router.post("/start")
def api_battle_start(data: dict = Body(default={}),
                     user=Depends(get_verified_telegram_user)):
    """Jang boshlaydi. mode: 'ranked' (reytingli) | 'bot' (mashq).

    'ranked' da avval kutayotgan raqib qidiriladi — bo'lsa DARHOL jonli
    jang bo'ladi; bo'lmasa yangi jang ochiladi.
    """
    tid = user["telegram_id"]
    mode = data.get("mode") or "ranked"
    if mode not in ("ranked", "bot"):
        raise HTTPException(status_code=400, detail="Noma'lum rejim")

    cat_id = db.safe_int(data.get("category_id")) or _ready_category()["id"]
    pool = _pool_for(cat_id)

    if mode == "ranked":
        waiting = db.find_waiting_chem_battle(cat_id, tid)
        if waiting and db.join_chem_battle(waiting["id"], tid):
            b = db.get_chem_battle(waiting["id"])
            return _start_response(b, tid, opponent_ready=True)

    # Bot rejimi yoki kutayotgan raqib yo'q — yangi jang.
    questions = cq.build_battle_questions(pool, count=db.BATTLE_QUESTION_COUNT)
    if not questions:
        raise HTTPException(status_code=400, detail="Savol yasab bo'lmadi — baza juda kichik.")

    if mode == "bot":
        elo = db.get_chem_rating(tid)["elo"]
        bid = db.create_chem_battle(cat_id, tid, questions, mode="bot",
                                    is_bot=1, bot_name="Kimyobot",
                                    bot_elo=max(600, elo + random.randint(-80, 80)))
    else:
        bid = db.create_chem_battle(cat_id, tid, questions, mode="ranked")

    return _start_response(db.get_chem_battle(bid), tid, opponent_ready=(mode == "bot"))


@router.post("/invite")
def api_battle_invite(data: dict = Body(default={}),
                      user=Depends(get_verified_telegram_user)):
    """Do'stga taklif — 6 belgili kod bilan yopiq jang yaratadi."""
    tid = user["telegram_id"]
    cat_id = db.safe_int(data.get("category_id")) or _ready_category()["id"]
    pool = _pool_for(cat_id)
    questions = cq.build_battle_questions(pool, count=db.BATTLE_QUESTION_COUNT)

    code = _new_code()
    bid = db.create_chem_battle(cat_id, tid, questions, mode="friend", invite_code=code)
    return {"battle_id": bid, "code": code, "total": len(questions)}


@router.post("/join-code")
def api_battle_join_code(data: dict = Body(...),
                         user=Depends(get_verified_telegram_user)):
    """Do'st bergan kod bilan jangga qo'shilish."""
    tid = user["telegram_id"]
    code = (data.get("code") or "").strip().upper()
    if len(code) != 6:
        raise HTTPException(status_code=400, detail="Kod 6 ta belgidan iborat bo'lishi kerak")

    b = db.find_chem_battle_by_code(code)
    if not b:
        raise HTTPException(status_code=404, detail="Bunday kod topilmadi yoki o'yin allaqachon boshlangan")
    if b["p1_telegram_id"] == tid:
        raise HTTPException(status_code=400, detail="O'z kodingizga qo'shila olmaysiz")
    if not db.join_chem_battle(b["id"], tid):
        raise HTTPException(status_code=400, detail="Bu o'yinga allaqachon boshqa kishi qo'shildi")

    return _start_response(db.get_chem_battle(b["id"]), tid, opponent_ready=True)


def _start_response(battle: dict, telegram_id: int, opponent_ready: bool):
    """Jang boshlanish javobi + serverdagi run holatini tayyorlash."""
    _RUNS[_run_key(battle["id"], telegram_id)] = {
        "index": 0, "asked_at": None, "score": 0, "time_ms": 0,
    }
    me = db.get_chem_rating(telegram_id)

    opp_name, opp_elo = None, None
    if battle["is_bot"]:
        opp_name, opp_elo = battle["bot_name"], battle["bot_elo"]
    else:
        other = battle["p2_telegram_id"] if battle["p1_telegram_id"] == telegram_id \
            else battle["p1_telegram_id"]
        if other:
            u = db.get_or_create_user(other, "Raqib")
            opp_name = u.get("first_name") or "Raqib"
            opp_elo = db.get_chem_rating(other)["elo"]

    return {
        "battle_id": battle["id"],
        "mode": battle["mode"],
        "total": len(battle["questions"]),
        "my_elo": me["elo"],
        "my_tier": me["tier"],
        "opponent_ready": opponent_ready,
        "opponent_name": opp_name,
        "opponent_elo": opp_elo,
    }


# --------------------------------------------------------------------------
#  O'yin: savol -> javob
# --------------------------------------------------------------------------

@router.get("/{battle_id}/question")
def api_battle_question(battle_id: int, user=Depends(get_verified_telegram_user)):
    """Navbatdagi savolni beradi (to'g'ri javobsiz)."""
    tid = user["telegram_id"]
    b = db.get_chem_battle(battle_id)
    if not b:
        raise HTTPException(status_code=404, detail="Jang topilmadi")
    if tid not in (b["p1_telegram_id"], b["p2_telegram_id"]):
        raise HTTPException(status_code=403, detail="Bu jang sizniki emas")

    run = _RUNS.get(_run_key(battle_id, tid))
    if run is None:
        # Server qayta ishga tushgan bo'lishi mumkin — boshidan boshlaymiz.
        run = {"index": 0, "asked_at": None, "score": 0, "time_ms": 0}
        _RUNS[_run_key(battle_id, tid)] = run

    if run["index"] >= len(b["questions"]):
        return {"finished": True}

    q = b["questions"][run["index"]]
    run["asked_at"] = time.time()
    return {
        "finished": False,
        "index": run["index"] + 1,
        "total": len(b["questions"]),
        "my_score": run["score"],
        "question": cq.strip_answers([q])[0],
    }


@router.post("/{battle_id}/answer")
def api_battle_answer(battle_id: int, data: dict = Body(...),
                      user=Depends(get_verified_telegram_user)):
    """Javobni SERVERDA tekshiradi va vaqtni SERVER o'lchaydi."""
    tid = user["telegram_id"]
    b = db.get_chem_battle(battle_id)
    if not b:
        raise HTTPException(status_code=404, detail="Jang topilmadi")
    if tid not in (b["p1_telegram_id"], b["p2_telegram_id"]):
        raise HTTPException(status_code=403, detail="Bu jang sizniki emas")

    run = _RUNS.get(_run_key(battle_id, tid))
    if run is None or run["index"] >= len(b["questions"]):
        raise HTTPException(status_code=400, detail="Bu jangda javob berish tugagan")

    q = b["questions"][run["index"]]
    given = (data.get("answer") or "").strip()
    is_correct = given == q["correct_answer"]

    # Vaqt: savol berilgandan javob kelguncha. Cheksiz o'ylashning oldini
    # olish uchun bitta savolga maksimum 20 soniya hisoblanadi.
    elapsed = (time.time() - run["asked_at"]) if run["asked_at"] else 20.0
    run["time_ms"] += int(min(elapsed, 20.0) * 1000)
    if is_correct:
        run["score"] += 1
    run["index"] += 1

    return {
        "correct": is_correct,
        "correct_answer": q["correct_answer"],
        "my_score": run["score"],
        "next_index": run["index"] + 1 if run["index"] < len(b["questions"]) else None,
        "finished": run["index"] >= len(b["questions"]),
    }


@router.post("/{battle_id}/finish")
def api_battle_finish(battle_id: int, user=Depends(get_verified_telegram_user)):
    """Javoblar tugagach natijani saqlaydi."""
    tid = user["telegram_id"]
    b = db.get_chem_battle(battle_id)
    if not b:
        raise HTTPException(status_code=404, detail="Jang topilmadi")

    run = _RUNS.pop(_run_key(battle_id, tid), None)
    score = run["score"] if run else 0
    time_ms = run["time_ms"] if run else 999999

    # Bot rejimida raqib natijasi shu yerda yasaladi — o'quvchi kutmaydi.
    if b["is_bot"] and b["p2_score"] is None:
        total = len(b["questions"])
        bot_score = max(0, min(total, score + random.randint(-2, 2)))
        with db.get_connection() as conn:
            conn.cursor().execute("""
                UPDATE chem_battles
                SET p2_score = ?, p2_time_ms = ?, p2_finished_at = CURRENT_TIMESTAMP,
                    status = 'playing'
                WHERE id = ?
            """, (bot_score, random.randint(25000, 70000), battle_id))
            conn.commit()

    db.save_chem_battle_run(battle_id, tid, score, time_ms)
    db.record_daily_activity(tid)
    return api_battle_status(battle_id, user)


@router.get("/{battle_id}/status")
def api_battle_status(battle_id: int, user=Depends(get_verified_telegram_user)):
    """Jang holati — natija tayyor bo'lmasa 'kutilmoqda' qaytadi."""
    tid = user["telegram_id"]
    b = db.get_chem_battle(battle_id)
    if not b:
        raise HTTPException(status_code=404, detail="Jang topilmadi")
    if tid not in (b["p1_telegram_id"], b["p2_telegram_id"]):
        raise HTTPException(status_code=403, detail="Bu jang sizniki emas")
    return _battle_view(b, tid)


def _battle_view(b: dict, tid: int):
    """Jangni "mening ko'zim bilan" ko'rinadigan holatga o'giradi."""
    is_p1 = b["p1_telegram_id"] == tid
    my_score = b["p1_score"] if is_p1 else b["p2_score"]
    opp_score = b["p2_score"] if is_p1 else b["p1_score"]
    my_before = b["p1_elo_before"] if is_p1 else b["p2_elo_before"]
    my_after = b["p1_elo_after"] if is_p1 else b["p2_elo_after"]

    if b["is_bot"]:
        opp_name = b["bot_name"] or "Kimyobot"
    else:
        other = b["p2_telegram_id"] if is_p1 else b["p1_telegram_id"]
        opp_name = (db.get_or_create_user(other, "Raqib").get("first_name") or "Raqib") \
            if other else None

    result = None
    if b["status"] == "finished":
        if b["winner_telegram_id"] is None:
            result = "draw"
        elif b["winner_telegram_id"] == tid:
            result = "win"
        else:
            result = "lose"

    rating = db.get_chem_rating(tid)
    return {
        "battle_id": b["id"],
        "status": b["status"],
        "mode": b["mode"],
        "total": len(b["questions"]),
        "my_score": my_score,
        "opponent_score": opp_score,
        "opponent_name": opp_name,
        "is_bot": bool(b["is_bot"]),
        "result": result,
        "elo_before": my_before,
        "elo_after": my_after,
        "elo_delta": (my_after - my_before) if (my_after is not None and my_before is not None) else 0,
        "my_elo": rating["elo"],
        "my_tier": rating["tier"],
    }


# --------------------------------------------------------------------------
#  Reyting, tarix, kunlik missiya
# --------------------------------------------------------------------------

@router.get("/me/rating")
def api_my_rating(user=Depends(get_verified_telegram_user)):
    tid = user["telegram_id"]
    return {
        "rating": db.get_chem_rating(tid),
        "daily_mission": db.get_chem_daily_mission(tid),
    }


@router.get("/me/history")
def api_my_battles(user=Depends(get_verified_telegram_user)):
    tid = user["telegram_id"]
    out = []
    for b in db.get_my_chem_battles(tid):
        is_p1 = b["p1_telegram_id"] == tid
        my = b["p1_score"] if is_p1 else b["p2_score"]
        opp = b["p2_score"] if is_p1 else b["p1_score"]
        if b["is_bot"]:
            name = b["bot_name"] or "Kimyobot"
        else:
            other = b["p2_telegram_id"] if is_p1 else b["p1_telegram_id"]
            name = (db.get_or_create_user(other, "Raqib").get("first_name") or "Raqib") \
                if other else "Raqib kutilmoqda"
        res = None
        if b["status"] == "finished":
            res = "draw" if b["winner_telegram_id"] is None else \
                  ("win" if b["winner_telegram_id"] == tid else "lose")
        before = b["p1_elo_before"] if is_p1 else b["p2_elo_before"]
        after = b["p1_elo_after"] if is_p1 else b["p2_elo_after"]
        out.append({
            "id": b["id"], "status": b["status"], "mode": b["mode"],
            "my_score": my, "opponent_score": opp, "opponent_name": name,
            "result": res, "is_bot": bool(b["is_bot"]),
            "elo_delta": (after - before) if (after is not None and before is not None) else 0,
            "created_at": b["created_at"],
        })
    return {"battles": out}


@router.get("/leaderboard")
def api_chem_leaderboard(user=Depends(get_verified_telegram_user)):
    tid = user["telegram_id"]
    rows = db.get_chem_leaderboard(50)
    me = db.get_chem_rating(tid)
    return {
        "leaders": rows,
        "me": {
            "telegram_id": tid, "elo": me["elo"], "rank": me["rank"],
            "tier": me["tier"], "wins": me["wins"], "losses": me["losses"],
            "in_list": any(r["telegram_id"] == tid for r in rows),
        },
    }
