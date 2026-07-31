# config.py
# MUHIM O'ZGARISH (Xavfsizlik yangilanishi):
# Endi maxfiy qiymatlar (token, parol hash, JWT kaliti) shu faylda EMAS,
# balki loyiha papkasidagi ".env" faylida saqlanadi. ".env" fayli hech qachon
# GitHub'ga yuklanmaydi (.gitignore ichida). Shu fayl faqat ularni o'qib oladi.
#
# Birinchi marta sozlash uchun ".env.example" faylini ".env" nomiga
# nusxalab, ichidagi qiymatlarni to'ldiring.

import os
import sys
from dotenv import load_dotenv

load_dotenv()  # loyiha papkasidagi .env faylini o'qiydi (agar mavjud bo'lsa)


def _require_env(key: str) -> str:
    """Majburiy muhit o'zgaruvchisini o'qiydi. Topilmasa — aniq xatolik bilan to'xtaydi
    (noto'g'ri/bo'sh sozlama bilan production'da ishga tushishning oldini oladi)."""
    value = os.environ.get(key)
    if not value:
        sys.exit(
            f"\n[XATOLIK] '{key}' muhit o'zgaruvchisi topilmadi.\n"
            f"Loyiha papkasida '.env' fayl borligini va unda {key}=... qatori "
            f"to'ldirilganini tekshiring. Namuna uchun '.env.example' fayliga qarang.\n"
        )
    return value


# ---------- MAJBURIY MAXFIY QIYMATLAR (.env ichida) ----------

BOT_TOKEN = _require_env("BOT_TOKEN")

# Parolning o'zi emas — bcrypt bilan xeshlangan varianti saqlanadi.
# Yangi parol hosil qilish uchun generate_password_hash.py skriptini ishlating.
ADMIN_PASSWORD_HASH = _require_env("ADMIN_PASSWORD_HASH")

# Admin sessiya tokenlarini (JWT) imzolash uchun tasodifiy maxfiy kalit.
JWT_SECRET_KEY = _require_env("JWT_SECRET_KEY")


# ---------- ODDIY (maxfiy bo'lmagan) SOZLAMALAR ----------

WEBAPP_URL = os.environ.get(
    "WEBAPP_URL",
    "https://behruzsayfiyev1-production-4a0a.up.railway.app"
)

BOT_USERNAME = os.environ.get("BOT_USERNAME", "Behruz_Sayfiyev1bot")

CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "@Behruz_Sayfiyev1")
CHANNEL_URL = os.environ.get("CHANNEL_URL", "https://t.me/Behruz_Sayfiyev1")

BRAND_NAME = os.environ.get("BRAND_NAME", "Behruz Sayfiyev")
BRAND_SUB = os.environ.get("BRAND_SUB", "ONLINE TA'LIM PLATFORMASI")

ADMIN_CONTACT_USERNAME = os.environ.get("ADMIN_CONTACT_USERNAME", "BehruzSayfiyev")

# Mini App ichida "Admin" bo'limini avtomatik ko'radigan (parolsiz) Telegram ID'lar.
# Bu ID'lar initData orqali KRIPTOGRAFIK TASDIQLANGANDAN keyingina ishonch bilan
# qabul qilinadi (auth.py -> get_verified_telegram_user). Shuning uchun bu yerda
# oddiy ro'yxat sifatida qolishi xavfsiz — headerdan o'g'irlab bo'lmaydi.
_admin_ids_raw = os.environ.get("ADMIN_TELEGRAM_IDS", "7558364715")
ADMIN_TELEGRAM_IDS = [int(x.strip()) for x in _admin_ids_raw.split(",") if x.strip()]

DB_PATH = os.environ.get("DB_PATH", "database.db")
