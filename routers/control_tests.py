# routers/control_tests.py
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from routers.deps import get_verified_telegram_user
import database as db

router = APIRouter(prefix="/api", tags=["control-tests"])

TEST_KIND_LEADERBOARD_KINDS = ("attestation", "certificate", "practice")


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


@router.get("/test-kind-leaderboard")
def api_test_kind_leaderboard(kind: str, year: int = None, month: int = None,
                              user=Depends(get_verified_telegram_user)):
    """Attestatsiya / Milliy sertifikat / Mavzuli testlar uchun alohida
    oylik reyting — get_control_test_leaderboard bilan bir xil shakl,
    lekin test_kind bo'yicha filtrlanadi."""
    if kind not in TEST_KIND_LEADERBOARD_KINDS:
        raise HTTPException(status_code=400, detail="Noto'g'ri reyting turi")
    now = datetime.now(timezone.utc)
    y = year or now.year
    m = month or now.month
    leaderboard = db.get_test_kind_monthly_leaderboard(kind, y, m)
    my_rank = db.get_my_test_kind_rank(user["telegram_id"], kind, y, m)
    return {"year": y, "month": m, "kind": kind, "leaderboard": leaderboard, "my_rank": my_rank}
