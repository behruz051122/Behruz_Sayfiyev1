# routers/user.py
from fastapi import APIRouter, Depends

from config import BOT_USERNAME, ADMIN_TELEGRAM_IDS
from routers.deps import get_verified_telegram_user
import database as db

router = APIRouter(prefix="/api", tags=["user"])


@router.get("/user")
def api_get_user(user=Depends(get_verified_telegram_user)):
    db_user = db.get_or_create_user(
        telegram_id=user["telegram_id"],
        first_name=user["first_name"],
        username=user.get("username"),
    )
    db_user["confirmed_referrals"] = db.get_confirmed_referral_count(user["telegram_id"])
    db_user["rank"] = db.get_user_rank(user["telegram_id"])
    return db_user


@router.get("/is-admin")
def api_is_admin(user=Depends(get_verified_telegram_user)):
    return {"is_admin": user["telegram_id"] in ADMIN_TELEGRAM_IDS}


@router.get("/referral-link")
def api_referral_link(user=Depends(get_verified_telegram_user)):
    telegram_id = user["telegram_id"]
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{telegram_id}"
    return {
        "link": link,
        "confirmed_referrals": db.get_confirmed_referral_count(telegram_id),
        "referrals": db.get_referral_progress(telegram_id),
    }


@router.get("/leaderboard")
def api_leaderboard(user=Depends(get_verified_telegram_user)):
    return {
        "leaderboard": db.get_leaderboard(100),
        "my_rank": db.get_user_rank(user["telegram_id"]),
    }


@router.get("/my-enrollments")
def api_my_enrollments(user=Depends(get_verified_telegram_user)):
    return {"enrollments": db.get_user_enrollments(user["telegram_id"])}
