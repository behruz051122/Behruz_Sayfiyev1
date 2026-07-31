# routers/admin_auth.py
from fastapi import APIRouter, Body, HTTPException, Request

from rate_limit import limiter
from config import ADMIN_PASSWORD_HASH, JWT_SECRET_KEY
import auth as auth_module

router = APIRouter(prefix="/api/admin", tags=["admin-auth"])


@router.post("/login")
@limiter.limit("5/15minutes")
def admin_login(request: Request, password: str = Body(..., embed=True)):
    if not auth_module.verify_password(password, ADMIN_PASSWORD_HASH):
        raise HTTPException(status_code=401, detail="Noto'g'ri parol")
    token = auth_module.create_admin_session_token(JWT_SECRET_KEY)
    return {"token": token, "expires_in_seconds": auth_module.ADMIN_TOKEN_TTL_SECONDS}
