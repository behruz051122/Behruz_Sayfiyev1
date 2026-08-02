# routers/simulators.py
from fastapi import APIRouter, Depends, HTTPException, Body

from routers.deps import get_verified_telegram_user
import database as db

router = APIRouter(prefix="/api", tags=["simulators"])


@router.get("/simulators")
def api_get_simulators(user=Depends(get_verified_telegram_user)):
    sims = db.get_all_simulators()
    for s in sims:
        subjects = db.get_simulator_subjects(s["id"])
        s["subjects"] = subjects
        s["total_questions"] = sum(x["question_count"] for x in subjects)
    return {"simulators": sims}


@router.post("/simulator/{simulator_id}/start")
def api_start_simulator(simulator_id: int, user=Depends(get_verified_telegram_user)):
    telegram_id = user["telegram_id"]
    db.get_or_create_user(telegram_id, user["first_name"], user.get("username"))
    result = db.start_simulator_attempt(telegram_id, simulator_id)
    if not result:
        raise HTTPException(status_code=400, detail="Bu simulyator uchun hozircha savollar yetarli emas")
    simulator = db.get_simulator(simulator_id)
    result["title"] = simulator["title"] if simulator else ""
    result["time_limit_seconds"] = simulator["time_limit_seconds"] if simulator else 10800
    return result


@router.get("/simulator/attempt/{attempt_id}/questions")
def api_get_simulator_questions(attempt_id: int, user=Depends(get_verified_telegram_user)):
    attempt = db.get_simulator_attempt(attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Urinish topilmadi")
    if attempt["telegram_id"] != user["telegram_id"]:
        raise HTTPException(status_code=403, detail="Bu urinish sizga tegishli emas")
    return {"questions": db.get_simulator_attempt_questions(attempt_id)}


def _get_owned_simulator_attempt_or_403(attempt_id: int, telegram_id: int) -> dict:
    attempt = db.get_simulator_attempt(attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Urinish topilmadi")
    if attempt["telegram_id"] != telegram_id:
        raise HTTPException(status_code=403, detail="Bu urinish sizga tegishli emas")
    return attempt


@router.post("/simulator/attempt/{attempt_id}/answer")
def api_submit_simulator_answer(attempt_id: int, data: dict = Body(...), user=Depends(get_verified_telegram_user)):
    telegram_id = user["telegram_id"]
    _get_owned_simulator_attempt_or_403(attempt_id, telegram_id)
    question_id = int(data["question_id"])
    selected_index = int(data["selected_index"])
    return db.submit_simulator_answer(telegram_id, attempt_id, question_id, selected_index)


@router.post("/simulator/attempt/{attempt_id}/finish")
def api_finish_simulator(attempt_id: int, user=Depends(get_verified_telegram_user)):
    _get_owned_simulator_attempt_or_403(attempt_id, user["telegram_id"])
    result = db.finish_simulator_attempt(attempt_id)
    if not result:
        raise HTTPException(status_code=404, detail="Urinish topilmadi")
    return result


@router.get("/my-simulator-results")
def api_my_simulator_results(user=Depends(get_verified_telegram_user)):
    return {"results": db.get_user_simulator_results(user["telegram_id"])}


@router.get("/my-progress-history")
def api_my_progress_history(user=Depends(get_verified_telegram_user)):
    return {"history": db.get_user_progress_history(user["telegram_id"])}
