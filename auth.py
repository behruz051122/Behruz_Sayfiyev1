# auth.py
# Xavfsizlik yadrosi: Telegram WebApp initData tasdiqlash, admin JWT sessiyalari,
# parolni xavfsiz hash qilish.
#
# NEGA KERAK:
# Mini App frontend'dan kelgan "telegram_id" yoki "ism"ga hech qachon shunchaki
# ISHONIB bo'lmaydi — buni brauzer konsolidan istalgan odam o'zgartirib yuborishi
# mumkin. Telegram esa har bir Mini App ochilishida "initData" degan, bot
# tokeningiz bilan HMAC-SHA256 orqali IMZOLANGAN satr beradi. Server shu imzoni
# qayta hisoblab, mos kelsa — bu so'rov haqiqatan ham Telegram orqali, haqiqatan
# ham ko'rsatilgan foydalanuvchidan kelganini 100% aniq biladi.
#
# Rasmiy algoritm: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl
from typing import Optional

import bcrypt
import jwt  # PyJWT


class TelegramAuthError(Exception):
    """initData tekshiruvidan o'tmagan so'rovlar uchun."""
    pass


# ---------- Telegram initData tasdiqlash ----------

def parse_and_verify_init_data(init_data: str, bot_token: str, max_age_seconds: int = 86400) -> dict:
    """
    Telegram Mini App'dan kelgan `initData` satrini tekshiradi.
    Muvaffaqiyatli bo'lsa — tasdiqlangan foydalanuvchi ma'lumotlarini qaytaradi.
    Muvaffaqiyatsiz bo'lsa — TelegramAuthError ko'taradi.

    HECH QACHON bu tekshiruvdan o'tmagan telegram_id'ga ishonmang.
    """
    if not init_data:
        raise TelegramAuthError("initData yuborilmagan (Mini App Telegram tashqarisida ochilganmi?)")

    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        raise TelegramAuthError("initData formati noto'g'ri")

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise TelegramAuthError("initData ichida imzo (hash) topilmadi")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise TelegramAuthError("Imzo mos kelmadi — bu so'rov soxta bo'lishi mumkin")

    auth_date = int(parsed.get("auth_date", 0))
    if max_age_seconds and (time.time() - auth_date) > max_age_seconds:
        raise TelegramAuthError("initData muddati o'tgan — Mini App'ni qayta oching")

    user_raw = parsed.get("user")
    if not user_raw:
        raise TelegramAuthError("initData ichida foydalanuvchi ma'lumoti yo'q")

    user = json.loads(user_raw)
    telegram_id = user.get("id")
    if not telegram_id:
        raise TelegramAuthError("Telegram ID aniqlanmadi")

    return {
        "telegram_id": int(telegram_id),
        "first_name": user.get("first_name") or "Foydalanuvchi",
        "username": user.get("username"),
        "auth_date": auth_date,
    }


# ---------- Admin parol hash ----------

def hash_password(plain_password: str) -> str:
    """Parolni bcrypt bilan hash qiladi. .env ga yozish uchun bir martalik ishlatiladi."""
    return bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
    except ValueError:
        return False


# ---------- Admin JWT sessiyasi ----------

ADMIN_TOKEN_TTL_SECONDS = 12 * 60 * 60  # 12 soat — shundan keyin qayta login talab qilinadi


def create_admin_session_token(secret_key: str, admin_label: str = "password_admin") -> str:
    payload = {
        "role": "admin",
        "sub": admin_label,
        "iat": int(time.time()),
        "exp": int(time.time()) + ADMIN_TOKEN_TTL_SECONDS,
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")


def verify_admin_session_token(token: str, secret_key: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        if payload.get("role") != "admin":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
