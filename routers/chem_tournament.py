# routers/chem_tournament.py
# ==========================================================================
#  KIMYO O'YINI — CHEMPIONAT
# ==========================================================================
# FORMAT:  saralash  ->  setka (chiqib ketish)  ->  final
#
#   1) Barcha qatnashchilar AYNAN BIR XIL 10 ta savolga javob beradi.
#   2) Ball (tenglikda — vaqt) bo'yicha yuqoridagi 2^k o'yinchi o'tadi.
#   3) Setkada har juftlik ham bir xil savollarga javob beradi. Bu
#      ASINXRON o'ynashga imkon beradi — ikkalasi bir vaqtda onlayn
#      bo'lishi shart emas, kim qachon ochsa o'shanda o'ynaydi.
#   4) Ikkala tomon javob berishi bilan g'olib avtomatik keyingi
#      bosqichga o'tadi. Hech kim qo'lda boshqarmaydi.
#
# ELO: faqat 8 va undan ko'p qatnashchi bo'lsa beriladi — kichik "uy
# chempionati" bilan reytingni sun'iy ko'tarishning oldini oladi.

import time

from fastapi import APIRouter, Depends, HTTPException, Body

from routers.deps import get_verified_telegram_user
import database as db
import chem_questions as cq

router = APIRouter(prefix="/api/chem/tournament", tags=["chem-tournament"])

# Saralash/setka o'yinlari uchun server tomonidagi run holati
# (battle bilan bir xil sabab: vaqtni va ballni server o'lchaydi).
_RUNS = {}


def _key(kind, ident, tid):
    return f"{kind}:{ident}:{tid}"


def _ready_category():
    cats = db.get_chem_categories(only_ready=True)
    if not cats:
        raise HTTPException(status_code=400, detail="Hozircha o'yinga tayyor bo'lim yo'q.")
    return cats[0]


# --------------------------------------------------------------------------
#  Ro'yxat, yaratish, qo'shilish
# --------------------------------------------------------------------------

@router.get("/list")
def api_tournament_list(user=Depends(get_verified_telegram_user)):
    tid = user["telegram_id"]
    items = []
    for t in db.list_chem_tournaments():
        joined = any(p["telegram_id"] == tid for p in db.get_chem_tournament(t["id"])["players"])
        items.append({
            "id": t["id"], "title": t["title"],
            "is_official": bool(t["is_official"]), "prize_text": t["prize_text"],
            "creator_name": t["creator_name"], "player_count": t["player_count"],
            "start_mode": t["start_mode"], "start_count": t["start_count"],
            "start_at": t["start_at"], "status": t["status"],
            "elo_counts": t["player_count"] >= db.TOURNAMENT_ELO_MIN_PLAYERS,
            "joined": joined,
        })
    return {"tournaments": items, "can_create": db.count_todays_tournaments_by(tid) == 0}


@router.post("/create")
def api_tournament_create(data: dict = Body(...), user=Depends(get_verified_telegram_user)):
    """O'quvchi chempionat yaratadi — bepul, sovrinsiz, faqat ELO raqobati."""
    tid = user["telegram_id"]
    if db.count_todays_tournaments_by(tid) >= 1:
        raise HTTPException(status_code=400,
                            detail="Kuniga bitta chempionat yaratish mumkin. Ertaga urinib ko'ring.")

    title = (data.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Chempionat nomi majburiy")
    if len(title) > 60:
        title = title[:60]

    start_mode = data.get("start_mode") or "count"
    if start_mode not in ("count", "time"):
        raise HTTPException(status_code=400, detail="Noma'lum boshlanish sharti")
    start_count = max(db.TOURNAMENT_MIN_PLAYERS, db.safe_int(data.get("start_count"), 8))
    start_at = data.get("start_at") if start_mode == "time" else None
    if start_mode == "time" and not start_at:
        raise HTTPException(status_code=400, detail="Boshlanish vaqtini kiriting")

    cat = _ready_category()
    new_id = db.create_chem_tournament(cat["id"], title, tid,
                                       start_mode=start_mode, start_count=start_count,
                                       start_at=start_at)
    db.join_chem_tournament(new_id, tid)   # yaratuvchi avtomatik qatnashadi
    return {"success": True, "id": new_id}


@router.post("/{tournament_id}/join")
def api_tournament_join(tournament_id: int, user=Depends(get_verified_telegram_user)):
    r = db.join_chem_tournament(tournament_id, user["telegram_id"])
    if not r["ok"]:
        raise HTTPException(status_code=400, detail=r["error"])
    maybe_start(tournament_id)
    return {"success": True, "already": r.get("already", False)}


def maybe_start(tournament_id: int):
    """Odam soni to'lgan bo'lsa chempionatni darhol boshlaydi.

    Vaqt bo'yicha boshlanadiganlarini fon vazifasi (bot.py) tekshiradi.
    """
    for t in db.get_startable_chem_tournaments():
        if t["id"] != tournament_id:
            continue
        pool = db.get_chem_substances_by_category(t["category_id"])
        qs = cq.build_battle_questions(pool, count=db.TOURNAMENT_QUESTION_COUNT)
        if qs:
            db.start_chem_tournament(tournament_id, qs)


# --------------------------------------------------------------------------
#  Holat va setka
# --------------------------------------------------------------------------

@router.get("/{tournament_id}")
def api_tournament_detail(tournament_id: int, user=Depends(get_verified_telegram_user)):
    tid = user["telegram_id"]
    t = db.get_chem_tournament(tournament_id)
    if not t:
        raise HTTPException(status_code=404, detail="Chempionat topilmadi")

    me = next((p for p in t["players"] if p["telegram_id"] == tid), None)
    my_match = db.get_my_chem_match(tournament_id, tid) if me else None

    # "Hozir nima qilishim kerak?" — talabaga bitta aniq harakat ko'rsatiladi.
    action = None
    if not me and t["status"] == "open":
        action = "join"
    elif me and t["status"] == "qualifying" and not me["qual_done"]:
        action = "qualify"
    elif my_match and t["status"] == "bracket":
        mine_done = (my_match["p1_done"] if my_match["p1_telegram_id"] == tid
                     else my_match["p2_done"])
        action = "wait_opponent" if mine_done else "play_match"
    elif me and t["status"] == "bracket":
        action = "eliminated" if me["eliminated_round"] is not None else "wait_round"

    return {
        "tournament": {
            "id": t["id"], "title": t["title"], "status": t["status"],
            "is_official": bool(t["is_official"]), "prize_text": t["prize_text"],
            "start_mode": t["start_mode"], "start_count": t["start_count"],
            "start_at": t["start_at"], "round_no": t["round_no"],
            "player_count": t["player_count"],
            "elo_counts": t["player_count"] >= db.TOURNAMENT_ELO_MIN_PLAYERS,
            "winner_telegram_id": t["winner_telegram_id"],
        },
        "players": [{
            "telegram_id": p["telegram_id"], "name": p["first_name"] or "O'quvchi",
            "qual_score": p["qual_score"], "qual_done": bool(p["qual_done"]),
            "seed": p["seed"], "place": p["place"],
            "eliminated_round": p["eliminated_round"],
            "is_me": p["telegram_id"] == tid,
        } for p in t["players"]],
        "bracket": _bracket_view(tournament_id, t),
        "my_action": action,
        "my_match_id": my_match["id"] if my_match else None,
    }


def _bracket_view(tournament_id: int, t: dict):
    names = {p["telegram_id"]: (p["first_name"] or "O'quvchi") for p in t["players"]}
    rounds = {}
    for m in db.get_chem_tournament_matches(tournament_id):
        rounds.setdefault(m["round_no"], []).append({
            "id": m["id"], "slot": m["slot"], "status": m["status"],
            "p1": names.get(m["p1_telegram_id"]), "p1_score": m["p1_score"],
            "p2": names.get(m["p2_telegram_id"]), "p2_score": m["p2_score"],
            "winner": names.get(m["winner_telegram_id"]),
        })
    return [{"round_no": r, "matches": rounds[r]} for r in sorted(rounds)]


# --------------------------------------------------------------------------
#  Saralash o'yini
# --------------------------------------------------------------------------

@router.get("/{tournament_id}/qual/question")
def api_qual_question(tournament_id: int, user=Depends(get_verified_telegram_user)):
    tid = user["telegram_id"]
    t = db.get_chem_tournament(tournament_id)
    if not t or t["status"] != "qualifying":
        raise HTTPException(status_code=400, detail="Saralash bosqichi faol emas")
    me = next((p for p in t["players"] if p["telegram_id"] == tid), None)
    if not me:
        raise HTTPException(status_code=403, detail="Siz bu chempionatda qatnashmayapsiz")
    if me["qual_done"]:
        return {"finished": True}

    import json as _json
    questions = _json.loads(t["qual_questions"] or "[]")
    return _serve_question(_key("qual", tournament_id, tid), questions)


@router.post("/{tournament_id}/qual/answer")
def api_qual_answer(tournament_id: int, data: dict = Body(...),
                    user=Depends(get_verified_telegram_user)):
    tid = user["telegram_id"]
    t = db.get_chem_tournament(tournament_id)
    if not t or t["status"] != "qualifying":
        raise HTTPException(status_code=400, detail="Saralash bosqichi faol emas")
    import json as _json
    questions = _json.loads(t["qual_questions"] or "[]")
    return _check_answer(_key("qual", tournament_id, tid), questions, data.get("answer"))


@router.post("/{tournament_id}/qual/finish")
def api_qual_finish(tournament_id: int, user=Depends(get_verified_telegram_user)):
    tid = user["telegram_id"]
    run = _RUNS.pop(_key("qual", tournament_id, tid), None)
    db.save_chem_qual_result(tournament_id, tid,
                             run["score"] if run else 0,
                             run["time_ms"] if run else 999999)
    db.record_daily_activity(tid)
    return api_tournament_detail(tournament_id, user)


# --------------------------------------------------------------------------
#  Setka o'yini
# --------------------------------------------------------------------------

@router.get("/match/{match_id}/question")
def api_match_question(match_id: int, user=Depends(get_verified_telegram_user)):
    tid = user["telegram_id"]
    m = _require_my_match(match_id, tid)
    if (m["p1_done"] if m["p1_telegram_id"] == tid else m["p2_done"]):
        return {"finished": True}
    return _serve_question(_key("match", match_id, tid), m["questions"])


@router.post("/match/{match_id}/answer")
def api_match_answer(match_id: int, data: dict = Body(...),
                     user=Depends(get_verified_telegram_user)):
    tid = user["telegram_id"]
    m = _require_my_match(match_id, tid)
    return _check_answer(_key("match", match_id, tid), m["questions"], data.get("answer"))


@router.post("/match/{match_id}/finish")
def api_match_finish(match_id: int, user=Depends(get_verified_telegram_user)):
    tid = user["telegram_id"]
    m = _require_my_match(match_id, tid)
    run = _RUNS.pop(_key("match", match_id, tid), None)
    db.save_chem_match_result(match_id, tid,
                              run["score"] if run else 0,
                              run["time_ms"] if run else 999999)
    db.record_daily_activity(tid)
    return api_tournament_detail(m["tournament_id"], user)


def _require_my_match(match_id: int, tid: int):
    m = db.get_chem_match(match_id)
    if not m:
        raise HTTPException(status_code=404, detail="O'yin topilmadi")
    if tid not in (m["p1_telegram_id"], m["p2_telegram_id"]):
        raise HTTPException(status_code=403, detail="Bu o'yin sizniki emas")
    if m["status"] == "finished":
        raise HTTPException(status_code=400, detail="Bu o'yin allaqachon yakunlangan")
    return m


# --------------------------------------------------------------------------
#  Umumiy: savol berish va javobni tekshirish
# --------------------------------------------------------------------------

def _serve_question(key: str, questions: list):
    """Savolni to'g'ri javobsiz beradi va vaqt hisobini boshlaydi."""
    run = _RUNS.get(key)
    if run is None:
        run = {"index": 0, "asked_at": None, "score": 0, "time_ms": 0}
        _RUNS[key] = run
    if run["index"] >= len(questions):
        return {"finished": True}

    run["asked_at"] = time.time()
    return {
        "finished": False,
        "index": run["index"] + 1,
        "total": len(questions),
        "my_score": run["score"],
        "question": cq.strip_answers([questions[run["index"]]])[0],
    }


def _check_answer(key: str, questions: list, given):
    """Javobni SERVERDA tekshiradi va vaqtni SERVER o'lchaydi."""
    run = _RUNS.get(key)
    if run is None or run["index"] >= len(questions):
        raise HTTPException(status_code=400, detail="Javob berish tugagan")

    q = questions[run["index"]]
    is_correct = (given or "").strip() == q["correct_answer"]
    elapsed = (time.time() - run["asked_at"]) if run["asked_at"] else 20.0
    run["time_ms"] += int(min(elapsed, 20.0) * 1000)
    if is_correct:
        run["score"] += 1
    run["index"] += 1

    return {
        "correct": is_correct,
        "correct_answer": q["correct_answer"],
        "my_score": run["score"],
        "finished": run["index"] >= len(questions),
    }
