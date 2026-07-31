# routers/deps.py
# Barcha routerlar uchun umumiy autentifikatsiya dependency'lari.
# Bir joyda saqlanadi — o'zgartirish kerak bo'lsa faqat shu yerni tahrirlash yetarli.

from fastapi import Header, HTTPException

from config import BOT_TOKEN, JWT_SECRET_KEY, ADMIN_TELEGRAM_IDS
import auth as auth_module


def get_verified_telegram_user(x_telegram_init_data: str = Header(default="")) -> dict:
    """
    Har bir 'himoyalangan' foydalanuvchi endpointi shu orqali chaqiruvchining
    HAQIQIY Telegram identifikatorini oladi. initData Telegram tomonidan bot
    tokeni bilan imzolangani uchun buni soxtalashtirib bo'lmaydi.
    """
    try:
        return auth_module.parse_and_verify_init_data(x_telegram_init_data, BOT_TOKEN)
    except auth_module.TelegramAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))


def require_admin(
    authorization: str = Header(default=""),
    x_telegram_init_data: str = Header(default=""),
) -> dict:
    """
    Admin endpointlari uchun. Ikki usuldan BIRI orqali o'tadi:
      1) Authorization: Bearer <JWT> — parol orqali login qilingan sessiya
      2) X-Telegram-Init-Data — tasdiqlangan telegram_id ADMIN_TELEGRAM_IDS
         ro'yxatida bo'lsa
    """
    if authorization.startswith("Bearer "):
        token = authorization[7:]
        payload = auth_module.verify_admin_session_token(token, JWT_SECRET_KEY)
        if payload:
            return {"method": "password_session"}

    if x_telegram_init_data:
        try:
            data = auth_module.parse_and_verify_init_data(x_telegram_init_data, BOT_TOKEN)
            if data["telegram_id"] in ADMIN_TELEGRAM_IDS:
                return {"method": "telegram_whitelist", "telegram_id": data["telegram_id"]}
        except auth_module.TelegramAuthError:
            pass

    raise HTTPException(status_code=401, detail="Admin huquqi tasdiqlanmadi")
