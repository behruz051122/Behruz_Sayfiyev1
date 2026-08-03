# routers/control_tests.py
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from routers.deps import get_verified_telegram_user
import database as db

router = APIRouter(prefix="/api", tags=["control-tests"])


@router.get("/control-tests")
def api_get_control_tests(user=Depends(get_verified_telegram_user)):
    return {"tests": db.get_control_tests_for_user(user["telegram_id"])}


@router.get("/control-test-leaderboard")
def api_control_test_leaderboard(year: int = None, month: int = None, user=Depends(get_verified_telegram_user)):
    now = datetime.now(timezone.utc)
    y = year or now.year
    m = month or now.month
    leaderboard = db.get_control_test_monthly_leaderboard(y, m)
    my_rank = db.get_my_control_test_rank(user["telegram_id"], y, m)
    return {"year": y, "month": m, "leaderboard": leaderboard, "my_rank": my_rank}
