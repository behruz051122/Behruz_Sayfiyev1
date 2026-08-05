# routers/games.py
# O'yinlar — 1x1 Battle (ELO reytingli, asinxron). Batafsili izoh
# database.py'dagi "O'YINLAR: 1x1 BATTLE" bo'limida.

from fastapi import APIRouter, Depends, HTTPException, Body

from routers.deps import get_verified_telegram_user
import database as db

router = APIRouter(prefix="/api/games", tags=["games"])


def _safe_question(q: dict) -> dict:
    """To'g'ri javobni (correct_index) MIJOZGA yubormaydigan xavfsiz nusxa —
    xuddi oddiy testlardagi kabi (routers/tests.py)."""
    return {
        "id": q["id"], "question_text": q["question_text"], "image_url": q["image_url"],
        "table_data": q.get("table_data"),
        "option_1": q["option_1"], "option_2": q["option_2"],
        "option_3": q["option_3"], "option_4": q["option_4"],
    }


def _enrich_battle(battle: dict, my_telegram_id: int) -> dict:
    """Battle dict'iga menga qulay maydonlarni qo'shadi: men qaysi
    o'yinchiman, raqibning ismi, natija tayyor bo'lsa g'olib kim."""
    is_p1 = battle["player1_telegram_id"] == my_telegram_id
    opponent_id = battle["player2_telegram_id"] if is_p1 else battle["player1_telegram_id"]
    opponent_name = None
    if opponent_id:
        opp_user = db.get_or_create_user(opponent_id, "Raqib")
        opponent_name = opp_user.get("first_name")

    my_score = battle["player1_score"] if is_p1 else battle["player2_score"]
    opp_score = battle["player2_score"] if is_p1 else battle["player1_score"]
    my_elo_after = battle["player1_elo_after"] if is_p1 else battle["player2_elo_after"]
    my_elo_before = battle["player1_elo_before"] if is_p1 else battle["player2_elo_before"]

    result = None
    if battle["status"] == "finished":
        if battle["winner_telegram_id"] is None:
            result = "draw"
        elif battle["winner_telegram_id"] == my_telegram_id:
            result = "win"
        else:
            result = "lose"

    return {
        **battle,
        "is_player1": is_p1,
        "opponent_telegram_id": opponent_id,
        "opponent_name": opponent_name,
        "my_score": my_score,
        "opponent_score": opp_score,
        "my_elo_before": my_elo_before,
        "my_elo_after": my_elo_after,
        "result": result,
    }


@router.get("/subjects")
def api_game_subjects(user=Depends(get_verified_telegram_user)):
    pools = db.get_battle_subjects_with_pool()
    ratings = {r["subject"]: r for r in db.get_my_ratings(user["telegram_id"])}
    subjects = []
    for p in pools:
        subject = p["subject"]
        rating = ratings.get(subject) or {"elo": db.BATTLE_STARTING_ELO, "wins": 0, "losses": 0, "draws": 0}
        subjects.append({
            "subject": subject,
            "question_pool_count": p["cnt"],
            "elo": rating["elo"],
            "tier": db.elo_tier_name(rating["elo"]),
            "wins": rating["wins"], "losses": rating["losses"], "draws": rating["draws"],
        })
    return {"subjects": subjects}


@router.post("/battle/join")
def api_battle_join(data: dict = Body(...), user=Depends(get_verified_telegram_user)):
    subject = (data.get("subject") or "").strip()
    if not subject:
        raise HTTPException(status_code=400, detail="Fan ko'rsatilmagan")

    pools = {p["subject"]: p["cnt"] for p in db.get_battle_subjects_with_pool()}
    if subject not in pools:
        raise HTTPException(status_code=400, detail="Bu fan bo'yicha hozircha yetarli savol yo'q")

    joined = db.join_or_create_battle(user["telegram_id"], subject)
    questions = [db.get_question(qid) for qid in joined["question_ids"]]
    questions = [_safe_question(q) for q in questions if q]
    return {"battle_id": joined["battle_id"], "role": joined["role"], "questions": questions}


@router.post("/battle/{battle_id}/submit")
def api_battle_submit(battle_id: int, data: dict = Body(...), user=Depends(get_verified_telegram_user)):
    battle = db.get_battle(battle_id)
    if not battle:
        raise HTTPException(status_code=404, detail="Jang topilmadi")
    if user["telegram_id"] not in (battle["player1_telegram_id"], battle["player2_telegram_id"]):
        raise HTTPException(status_code=403, detail="Bu jangga aloqangiz yo'q")

    answers = data.get("answers") or {}
    time_seconds = int(data.get("time_seconds") or 0)

    score = 0
    for qid_str, selected_index in answers.items():
        question = db.get_question(int(qid_str))
        if question and question["correct_index"] == selected_index:
            score += 1

    updated = db.submit_battle_result(battle_id, user["telegram_id"], score, time_seconds)
    if not updated:
        raise HTTPException(status_code=400, detail="Natija saqlanmadi")
    return _enrich_battle(updated, user["telegram_id"])


@router.get("/battle/{battle_id}")
def api_battle_status(battle_id: int, user=Depends(get_verified_telegram_user)):
    battle = db.get_battle(battle_id)
    if not battle:
        raise HTTPException(status_code=404, detail="Jang topilmadi")
    if user["telegram_id"] not in (battle["player1_telegram_id"], battle["player2_telegram_id"]):
        raise HTTPException(status_code=403, detail="Bu jangga aloqangiz yo'q")
    return _enrich_battle(battle, user["telegram_id"])


@router.get("/my-battles")
def api_my_battles(user=Depends(get_verified_telegram_user)):
    battles = db.get_my_battles(user["telegram_id"])
    return {"battles": [_enrich_battle(b, user["telegram_id"]) for b in battles]}


@router.get("/leaderboard/{subject}")
def api_game_leaderboard(subject: str, user=Depends(get_verified_telegram_user)):
    return {"leaderboard": db.get_battle_leaderboard(subject)}
